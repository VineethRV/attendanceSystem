import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import db
import crud
import sqlite3


class BackendGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Backend Admin GUI")
        self.geometry("900x600")
        db.init_db()

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        self.student_frame = ttk.Frame(nb)
        self.classroom_frame = ttk.Frame(nb)
        self.classes_frame = ttk.Frame(nb)
        self.attendance_frame = ttk.Frame(nb)

        nb.add(self.student_frame, text="Students")
        nb.add(self.classroom_frame, text="Classrooms")
        nb.add(self.classes_frame, text="Classes")
        nb.add(self.attendance_frame, text="Attendance")

        self._build_students_tab()
        self._build_classrooms_tab()
        self._build_classes_tab()
        self._build_attendance_tab()

    def _build_students_tab(self):
        f = self.student_frame
        left = ttk.Frame(f)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        right = ttk.Frame(f)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(left, text="USN").pack()
        self.s_usn = ttk.Entry(left)
        self.s_usn.pack()
        ttk.Label(left, text="Name").pack()
        self.s_name = ttk.Entry(left)
        self.s_name.pack()
        ttk.Label(left, text="Class").pack()
        self.s_class = ttk.Entry(left)
        self.s_class.pack()
        ttk.Label(left, text="Embedding (JSON)").pack()
        self.s_embed = ttk.Entry(left)
        self.s_embed.pack()

        ttk.Button(left, text="Add / Update", command=self.add_update_student).pack(pady=6)
        ttk.Button(left, text="Refresh List", command=self.refresh_students).pack()

        self.students_list = tk.Listbox(right)
        self.students_list.pack(fill=tk.BOTH, expand=True)
        self.students_list.bind("<<ListboxSelect>>", self.on_student_select)

        self.refresh_students()

    def add_update_student(self):
        usn = self.s_usn.get().strip()
        name = self.s_name.get().strip()
        class_name = self.s_class.get().strip() or None
        embedding = self.s_embed.get().strip() or None
        if not usn or not name:
            messagebox.showerror("Error", "USN and Name are required")
            return
        try:
            existing = crud.get_student(usn)
            if existing:
                # update
                try:
                    crud.update_student_embedding(usn, embedding)
                    conn = db.get_connection()
                    conn.execute("UPDATE students SET name = ?, class_name = ? WHERE usn = ?", (name, class_name, usn))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    messagebox.showerror("DB Error", str(e))
                    return
            else:
                crud.add_student(usn, name, class_name, embedding)
            messagebox.showinfo("OK", "Student added/updated")
            self.refresh_students()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("DB Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_students(self):
        try:
            rows = crud.list_students()
            self.students_list.delete(0, tk.END)
            for s in rows:
                self.students_list.insert(tk.END, f"{s['usn']} | {s['name']} | {s.get('class_name')} | {s.get('embedding')}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_student_select(self, evt):
        try:
            sel = self.students_list.curselection()
            if not sel:
                return
            idx = sel[0]
            text = self.students_list.get(idx)
            usn = text.split("|")[0].strip()
            s = crud.get_student(usn)
            if s:
                self.s_usn.delete(0, tk.END)
                self.s_usn.insert(0, s['usn'])
                self.s_name.delete(0, tk.END)
                self.s_name.insert(0, s['name'])
                self.s_class.delete(0, tk.END)
                self.s_class.insert(0, s.get('class_name') or "")
                self.s_embed.delete(0, tk.END)
                self.s_embed.insert(0, s.get('embedding') or "")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _build_classrooms_tab(self):
        f = self.classroom_frame
        left = ttk.Frame(f)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        right = ttk.Frame(f)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(left, text="Classroom").pack()
        self.c_room = ttk.Entry(left)
        self.c_room.pack()
        ttk.Label(left, text="Router IP").pack()
        self.c_ip = ttk.Entry(left)
        self.c_ip.pack()
        ttk.Button(left, text="Add / Update", command=self.add_update_classroom).pack(pady=6)
        ttk.Button(left, text="Refresh List", command=self.refresh_classrooms).pack()

        self.classrooms_list = tk.Listbox(right)
        self.classrooms_list.pack(fill=tk.BOTH, expand=True)
        self.classrooms_list.bind("<<ListboxSelect>>", self.on_classroom_select)
        self.refresh_classrooms()

    def add_update_classroom(self):
        room = self.c_room.get().strip()
        ip = self.c_ip.get().strip() or None
        if not room:
            messagebox.showerror("Error", "Classroom is required")
            return
        try:
            existing = crud.get_classroom(room)
            if existing:
                conn = db.get_connection()
                conn.execute("UPDATE classrooms SET router_ip = ? WHERE classroom = ?", (ip, room))
                conn.commit()
                conn.close()
            else:
                crud.add_classroom(room, ip)
            messagebox.showinfo("OK", "Classroom added/updated")
            self.refresh_classrooms()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("DB Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_classrooms(self):
        try:
            rows = crud.list_classrooms()
            self.classrooms_list.delete(0, tk.END)
            for r in rows:
                self.classrooms_list.insert(tk.END, f"{r['classroom']} | {r.get('router_ip')}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_classroom_select(self, evt):
        sel = self.classrooms_list.curselection()
        if not sel:
            return
        idx = sel[0]
        text = self.classrooms_list.get(idx)
        room = text.split("|")[0].strip()
        r = crud.get_classroom(room)
        if r:
            self.c_room.delete(0, tk.END)
            self.c_room.insert(0, r['classroom'])
            self.c_ip.delete(0, tk.END)
            self.c_ip.insert(0, r.get('router_ip') or "")

    def _build_classes_tab(self):
        f = self.classes_frame
        top = ttk.Frame(f)
        top.pack(fill=tk.X, padx=8, pady=8)
        bottom = ttk.Frame(f)
        bottom.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(top, text="Class Name").grid(row=0, column=0)
        self.cl_class = ttk.Entry(top)
        self.cl_class.grid(row=0, column=1)
        ttk.Label(top, text="Start Time (HH:MM)").grid(row=1, column=0)
        self.cl_start = ttk.Entry(top)
        self.cl_start.grid(row=1, column=1)
        ttk.Label(top, text="Subject").grid(row=2, column=0)
        self.cl_subject = ttk.Entry(top)
        self.cl_subject.grid(row=2, column=1)
        ttk.Label(top, text="Classroom").grid(row=3, column=0)
        self.cl_room = ttk.Entry(top)
        self.cl_room.grid(row=3, column=1)

        ttk.Button(top, text="Add", command=self.add_class_schedule).grid(row=4, column=0, pady=6)
        ttk.Button(top, text="Refresh", command=self.refresh_classes).grid(row=4, column=1)

        self.classes_list = tk.Listbox(bottom)
        self.classes_list.pack(fill=tk.BOTH, expand=True)
        self.classes_list.bind("<<ListboxSelect>>", self.on_class_select)
        self.refresh_classes()

    def add_class_schedule(self):
        class_name = self.cl_class.get().strip()
        start_time = self.cl_start.get().strip()
        subject = self.cl_subject.get().strip() or None
        classroom = self.cl_room.get().strip() or None
        if not class_name or not start_time:
            messagebox.showerror("Error", "Class name and start time are required")
            return
        try:
            crud.add_class_schedule(class_name, start_time, subject, classroom)
            messagebox.showinfo("OK", "Class schedule added")
            self.refresh_classes()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("DB Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_classes(self):
        try:
            # show all classes
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT class_name, start_time, subject, classroom FROM classes ORDER BY class_name, start_time")
            rows = cur.fetchall()
            conn.close()
            self.classes_list.delete(0, tk.END)
            for r in rows:
                self.classes_list.insert(tk.END, f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_class_select(self, evt):
        sel = self.classes_list.curselection()
        if not sel:
            return
        idx = sel[0]
        text = self.classes_list.get(idx)
        parts = [p.strip() for p in text.split('|')]
        if len(parts) >= 4:
            self.cl_class.delete(0, tk.END)
            self.cl_class.insert(0, parts[0])
            self.cl_start.delete(0, tk.END)
            self.cl_start.insert(0, parts[1])
            self.cl_subject.delete(0, tk.END)
            self.cl_subject.insert(0, parts[2])
            self.cl_room.delete(0, tk.END)
            self.cl_room.insert(0, parts[3])

    def _build_attendance_tab(self):
        f = self.attendance_frame
        left = ttk.Frame(f)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        right = ttk.Frame(f)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(left, text="USN").pack()
        self.a_usn = ttk.Entry(left)
        self.a_usn.pack()
        ttk.Label(left, text="Subject").pack()
        self.a_subject = ttk.Entry(left)
        self.a_subject.pack()
        ttk.Label(left, text="Percentage").pack()
        self.a_pct = ttk.Entry(left)
        self.a_pct.pack()

        ttk.Button(left, text="Set Attendance", command=self.set_attendance).pack(pady=6)
        ttk.Button(left, text="Refresh", command=self.refresh_attendance).pack()

        self.att_list = tk.Listbox(right)
        self.att_list.pack(fill=tk.BOTH, expand=True)
        self.refresh_attendance()

    def set_attendance(self):
        usn = self.a_usn.get().strip()
        subject = self.a_subject.get().strip()
        pct_raw = self.a_pct.get().strip()
        if not usn or not subject or not pct_raw:
            messagebox.showerror("Error", "USN, subject and percentage are required")
            return
        try:
            pct = float(pct_raw)
        except ValueError:
            messagebox.showerror("Error", "Invalid percentage")
            return
        try:
            crud.set_attendance(usn, subject, pct)
            messagebox.showinfo("OK", "Attendance set")
            self.refresh_attendance()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_attendance(self):
        try:
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT usn, subject, percentage FROM attendance ORDER BY usn, subject")
            rows = cur.fetchall()
            conn.close()
            self.att_list.delete(0, tk.END)
            for r in rows:
                self.att_list.insert(tk.END, f"{r[0]} | {r[1]} | {r[2]}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    app = BackendGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
