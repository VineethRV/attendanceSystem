from flask import Flask, request, jsonify, Response, make_response
from flask_cors import CORS
import json
import base64
import io
import csv
import sqlite3

import config
import db
import crud


def create_app():
    app = Flask(__name__)
    CORS(app, origins=config.ALLOWED_ORIGINS)

    # Ensure CORS headers are always set for allowed origins, including for
    # requests where Flask-CORS might not inject them (HEAD or other edge cases).
    @app.after_request
    def _apply_cors_headers(response):
        origin = request.headers.get('Origin')
        try:
            allowed = config.ALLOWED_ORIGINS
        except Exception:
            allowed = []
        if origin and origin in allowed:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    def _get_client_ip():
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return request.remote_addr

    def _require_basic_auth():
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return None
        try:
            token = auth.split(" ", 1)[1]
            decoded = base64.b64decode(token).decode("utf-8")
            user, pwd = decoded.split(":", 1)
            return (user, pwd)
        except Exception:
            return None

    def _check_admin():
        creds = _require_basic_auth()
        if not creds:
            return False
        user, pwd = creds
        return user == config.ADMIN_USER and pwd == config.ADMIN_PASS

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({"status": "ok", "backend": config.BACKEND_URL})

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"})

    @app.route("/api/register", methods=["POST"])
    def register():
        # Debug: log request metadata to help diagnose CORS / TLS issues
        try:
            print("--- /api/register incoming request ---")
            print("URL:", request.url)
            print("Remote Addr:", request.remote_addr)
            print("Is secure (HTTPS):", request.is_secure)
            print("Origin header:", request.headers.get('Origin'))
            # print headers (truncated)
            for k, v in list(request.headers.items())[:20]:
                print(f"Header: {k}: {v}")
            raw = request.get_data()
            try:
                print("Raw body (first 1000 bytes):", raw[:1000])
            except Exception:
                print("Raw body present (binary) length:", len(raw))
            data = request.get_json(force=True)
            print("Parsed JSON:", data)
        except Exception as e:
            print("Error parsing request JSON:", e)
            raw = request.get_data()
            print("Raw body on error (first 200 bytes):", raw[:200])
            return jsonify({"error": "Invalid JSON", "details": str(e)}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "JSON body must be an object"}), 400

        # Accept either legacy fields (name/usn/embedding) or the frontend's
        # `student_id` and `embeddings` payload.
        name = data.get("name") or data.get("Name")
        usn = (
            data.get("usn")
            or data.get("USN")
            or data.get("student_id")
            or data.get("studentId")
            or data.get("id")
        )
        embeddings = (
            data.get("embeddings")
            or data.get("embeds")
            or data.get("embedding")
            or data.get("embedding_vector")
            or data.get("Embedding")
        )

        if not usn or embeddings is None:
            return jsonify({"error": "Missing required fields: student_id/usn and embeddings/embedding"}), 400

        # Normalize embeddings: support a single vector or a list of captured vectors.
        try:
            import ast

            def _to_float_list(v):
                if isinstance(v, list):
                    return [float(x) for x in v]
                if isinstance(v, str):
                    try:
                        return [float(x) for x in json.loads(v)]
                    except Exception:
                        return [float(x) for x in ast.literal_eval(v)]
                raise ValueError("Unsupported embedding type")

            # If embeddings is a list of vectors, average them element-wise.
            if isinstance(embeddings, list) and len(embeddings) > 0 and all(isinstance(el, list) for el in embeddings):
                vecs = [_to_float_list(el) for el in embeddings]
                if not vecs:
                    raise ValueError("Empty embeddings list")
                dim = len(vecs[0])
                for v in vecs:
                    if len(v) != dim:
                        raise ValueError("Embedding vectors must have the same dimension")
                avg = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
                vector = avg
            else:
                # Single vector (list or JSON-string)
                vector = _to_float_list(embeddings)
        except Exception as e:
            return jsonify({"error": "Invalid embeddings format", "details": str(e)}), 400

        try:
            embedding_str = json.dumps(vector)
        except Exception as e:
            return jsonify({"error": "Failed to serialize embedding", "details": str(e)}), 400

        client_ip = _get_client_ip()

        try:
            existing = crud.get_student(usn)
            if existing:
                crud.update_student_embedding(usn, embedding_str)
            else:
                # name/class_name optional for registration flow
                crud.add_student(usn, name or None, None, embedding_str)
        except sqlite3.IntegrityError as e:
            return jsonify({"error": "Database integrity error", "details": str(e)}), 400
        except Exception as e:
            return jsonify({"error": "Database error", "details": str(e)}), 500

        return jsonify({"status": "ok", "usn": usn, "ip": client_ip}), 201

    @app.route("/api/verify", methods=["POST"])
    def verify():
        # Debug: log request metadata for troubleshooting
        try:
            print("--- /api/verify incoming request ---")
            print("URL:", request.url)
            print("Remote Addr:", request.remote_addr)
            print("Is secure (HTTPS):", request.is_secure)
            print("Origin header:", request.headers.get('Origin'))
            for k, v in list(request.headers.items())[:20]:
                print(f"Header: {k}: {v}")
            raw = request.get_data()
            try:
                print("Raw body (first 1000 bytes):", raw[:1000])
            except Exception:
                print("Raw body present (binary) length:", len(raw))
            payload = request.get_json(force=True)
            print("Parsed JSON:", payload)
        except Exception as e:
            print("Error parsing request JSON:", e)
            raw = request.get_data()
            print("Raw body on error (first 200 bytes):", raw[:200])
            return jsonify({"error": "Invalid JSON", "details": str(e)}), 400

        if not isinstance(payload, dict):
            return jsonify({"error": "JSON object expected"}), 400

        # Accept multiple field names from different frontends
        usn = payload.get("usn") or payload.get("USN") or payload.get("student_id") or payload.get("studentId")
        live_embedding = payload.get("embedding") or payload.get("live_embedding") or payload.get("liveEmbedding") or payload.get("liveEmbeds") or payload.get("live_embeddings")

        # If frontend sends multiple live embeddings, average them into one vector
        try:
            if live_embedding is None and "live_embeddings" in payload:
                le = payload.get("live_embeddings")
                if isinstance(le, list) and len(le) > 0 and isinstance(le[0], list):
                    length = len(le[0])
                    avg = [0.0] * length
                    for vec in le:
                        if not isinstance(vec, list) or len(vec) != length:
                            raise ValueError("Inconsistent live embedding lengths")
                        for i, v in enumerate(vec):
                            avg[i] += float(v)
                    live_embedding = [x / len(le) for x in avg]
        except Exception as e:
            return jsonify({"error": "Invalid live embedding format", "details": str(e)}), 400

        if not usn or live_embedding is None:
            return jsonify({"error": "Missing required fields: usn/student_id and embedding"}), 400

        client_ip = _get_client_ip()

        from datetime import datetime
        from math import sqrt
        import ast

        def same_subnet(ip1: str, ip2: str, mask_bits: int = 24) -> bool:
            try:
                a = ip1.split('.')
                b = ip2.split('.')
                if len(a) == 4 and len(b) == 4 and mask_bits == 24:
                    return a[0:3] == b[0:3]
                return ip1 == ip2
            except Exception:
                return False

        def to_float_list(v):
            if isinstance(v, list):
                return [float(x) for x in v]
            if isinstance(v, str):
                try:
                    return [float(x) for x in json.loads(v)]
                except Exception:
                    try:
                        return [float(x) for x in ast.literal_eval(v)]
                    except Exception:
                        raise ValueError("Cannot parse embedding")
            raise ValueError("Unsupported embedding type")

        def cosine_similarity(a, b):
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            na = sqrt(sum(x * x for x in a))
            nb = sqrt(sum(y * y for y in b))
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

        student = crud.get_student(usn)
        if not student:
            return jsonify({"error": "Unknown USN"}), 404

        class_name = student.get("class_name")
        if not class_name:
            return jsonify({"error": "Student has no class assigned"}), 400

        now = datetime.now()
        now_str = now.strftime("%H:%M")
        schedule = crud.get_class_schedule(class_name, now_str)
        if not schedule:
            schedules = crud.list_schedules_for_class(class_name)
            schedule = None
            for s in schedules:
                st = s.get("start_time") or ""
                if st.startswith(now.strftime("%H")):
                    schedule = s
                    break

        if not schedule:
            return jsonify({"error": "No active class found for this student at this time"}), 400

        classroom = schedule.get("classroom")
        if not classroom:
            return jsonify({"error": "Classroom not set for the scheduled class"}), 400

        room = crud.get_classroom(classroom)
        if not room or not room.get("router_ip"):
            return jsonify({"error": "Router IP not configured for classroom"}), 400

        router_ip = room.get("router_ip")

        if not same_subnet(router_ip, client_ip):
            return jsonify({"error": "Client IP not on expected classroom subnet", "client_ip": client_ip, "router_ip": router_ip}), 403

        try:
            stored_emb = student.get("embedding")
            stored_vec = to_float_list(stored_emb) if stored_emb is not None else []
            live_vec = to_float_list(live_embedding)
        except ValueError as e:
            return jsonify({"error": "Invalid embedding format", "details": str(e)}), 400

        sim = cosine_similarity(stored_vec, live_vec)
        THRESHOLD = 0.75
        if sim < THRESHOLD:
            return jsonify({"error": "Embedding mismatch", "similarity": sim}), 401

        subject = schedule.get("subject")
        if not subject:
            return jsonify({"error": "Subject not defined for this class"}), 400

        try:
            existing = crud.get_attendance(usn, subject)
            if existing and existing.get("percentage") is not None:
                new_pct = min(100.0, float(existing.get("percentage")) + 1.0)
            else:
                new_pct = 100.0
            crud.set_attendance(usn, subject, new_pct)
        except Exception as e:
            return jsonify({"error": "Failed to update attendance", "details": str(e)}), 500

        return jsonify({"status": "verified", "usn": usn, "subject": subject, "similarity": sim, "attendance": new_pct}), 200

    @app.route("/api/admin/stats", methods=["GET"])
    def admin_stats():
        if not _check_admin():
            return Response("Unauthorized", 401, {"WWW-Authenticate": "Basic realm=\"Admin\""})
        conn = db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM students")
            students = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM classrooms")
            classrooms = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM classes")
            classes = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM attendance")
            attendance = cur.fetchone()[0]
        finally:
            conn.close()
        return jsonify({"students": students, "classrooms": classrooms, "classes": classes, "attendance_records": attendance})

    @app.route("/api/admin/attendance", methods=["GET"])
    def admin_attendance():
        if not _check_admin():
            return Response("Unauthorized", 401, {"WWW-Authenticate": "Basic realm=\"Admin\""})
        conn = db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT usn, subject, percentage FROM attendance")
            data = [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]
        finally:
            conn.close()
        return jsonify(data)

    @app.route("/api/admin/export", methods=["GET"])
    def admin_export():
        if not _check_admin():
            return Response("Unauthorized", 401, {"WWW-Authenticate": "Basic realm=\"Admin\""})
        table = request.args.get("table", "students")
        conn = db.get_connection()
        cur = conn.cursor()
        try:
            if table == "students":
                cur.execute("SELECT usn, name, class_name, embedding FROM students")
            elif table == "attendance":
                cur.execute("SELECT usn, subject, percentage FROM attendance")
            else:
                return jsonify({"error": "unknown table"}), 400
            rows = cur.fetchall()
            headers = [c[0] for c in cur.description]
        finally:
            conn.close()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
        csv_data = buf.getvalue()
        resp = make_response(csv_data)
        resp.headers["Content-Type"] = "text/csv"
        resp.headers["Content-Disposition"] = f"attachment; filename={table}.csv"
        return resp

    return app


if __name__ == "__main__":
    import argparse
    import os
    parser = argparse.ArgumentParser(description="Run main_fixed server")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--cert", help="Path to TLS certificate (PEM)")
    parser.add_argument("--key", help="Path to TLS key (PEM)")
    args = parser.parse_args()

    ssl_cert = args.cert or os.environ.get("SSL_CERT")
    ssl_key = args.key or os.environ.get("SSL_KEY")
    ssl_context = None
    if ssl_cert and ssl_key:
        if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
            ssl_context = (ssl_cert, ssl_key)
        else:
            import logging
            logging.error("SSL cert/key not found: %s %s", ssl_cert, ssl_key)

    app = create_app()
    app.run(host=args.host, port=args.port, ssl_context=ssl_context)
