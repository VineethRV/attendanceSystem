import db
import crud

def run_smoke_test():
    print("Initializing DB...")
    db.init_db()

    print("Adding sample classroom...")
    crud.add_classroom("Room101", "192.168.1.10")

    print("Adding sample student...")
    crud.add_student("USN001", "Alice", "10A", "[0.1,0.2,0.3]")

    print("Setting attendance...")
    crud.set_attendance("USN001", "Math", 95.0)

    print("Adding class schedule...")
    crud.add_class_schedule("10A", "08:00", "Math", "Room101")

    print("Student record:")
    print(crud.get_student("USN001"))

    print("Classroom record:")
    print(crud.get_classroom("Room101"))

    print("Class schedule:")
    print(crud.get_class_schedule("10A", "08:00"))

    print("Attendance:")
    print(crud.get_attendance("USN001", "Math"))

if __name__ == "__main__":
    run_smoke_test()
