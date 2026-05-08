from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_connection

def build_tree(data):
    lookup = {}
    roots = []

    # Step 1: Create all nodes
    for emp in data:
        lookup[emp['Id']] = {
            "id": emp['Id'],
            "name": emp['Name'],
            "children": []
        }

    # Step 2: Build hierarchy
    for emp in data:
        if emp['ManagerId'] is None:
            # Root employee (CEO level)
            roots.append(lookup[emp['Id']])
        else:
            parent = lookup.get(emp['ManagerId'])
            if parent:
                parent['children'].append(lookup[emp['Id']])

    return roots

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Backend Running 🚀"

@app.route('/test-db')
def test_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DATABASE();")
    db_name = cursor.fetchone()

    return f"Connected to: {db_name}"

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM UserLogin WHERE Username=%s", (username,))
    user = cursor.fetchone()

    if not user:
        return {"message": "User not found"}, 401

    if user['Password'] != password:
        return {"message": "Wrong password"}, 401

    return {"message": "Login successful"}

@app.route('/add-department', methods=['POST'])
def add_department():
    data = request.json
    name = data.get('name')

    conn = get_connection()
    cursor = conn.cursor()

    # ✅ FIXED HERE
    cursor.execute("SELECT * FROM Department WHERE LOWER(Name)=LOWER(%s)", (name,))
    
    if cursor.fetchone():
        return {"message": "Department already exists"}, 400

    cursor.execute("INSERT INTO Department (Name) VALUES (%s)", (name,))
    conn.commit()

    return {"message": "Department added successfully"}

@app.route('/add-employee', methods=['POST'])
def add_employee():
    data = request.json

    name = data.get('name')
    dept_id = data.get('dept_id')
    dob = data.get('dob')
    address = data.get('address')
    designation = data.get('designation')
    manager_id = data.get('manager_id')

    conn = get_connection()
    cursor = conn.cursor()

    # Insert employee
    cursor.execute("""
        INSERT INTO Employee (DeptId, Name, Dob, Address, Designation, ManagerId)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (dept_id, name, dob, address, designation, manager_id))

    conn.commit()

    return {"message": "Employee added successfully"}

@app.route('/employee-tree', methods=['GET'])
def employee_tree():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    WITH RECURSIVE emp_tree AS (
        -- Top level (CEO / no manager)
        SELECT Id, Name, ManagerId, 1 AS level
        FROM Employee
        WHERE ManagerId IS NULL

        UNION ALL

        -- Subordinates
        SELECT e.Id, e.Name, e.ManagerId, et.level + 1
        FROM Employee e
        JOIN emp_tree et ON e.ManagerId = et.Id
    )
    SELECT * FROM emp_tree;
    """

    cursor.execute(query)
    data = cursor.fetchall()
    tree = build_tree(data)

    return tree

@app.route('/employees', methods=['GET'])
def get_employees():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        e.Id,
        e.Name,
        e.DeptId,
        e.ManagerId,
        e.Dob,
        e.Address,
        e.Designation,
        d.Name AS DeptName,
        m.Name AS ManagerName
    FROM Employee e
    LEFT JOIN Department d ON e.DeptId = d.id
    LEFT JOIN Employee m ON e.ManagerId = m.Id;
    """

    cursor.execute(query)
    data = cursor.fetchall()

    return jsonify(data)

@app.route('/departments', methods=['GET'])
def get_departments():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Department")
    data = cursor.fetchall()

    return jsonify(data)

@app.route('/delete-employee/<int:id>', methods=['DELETE'])
def delete_employee(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Employee WHERE Id=%s", (id,))
    conn.commit()

    return {"message": "Employee deleted successfully"}

@app.route('/update-employee/<int:id>', methods=['PUT'])
def update_employee(id):
    data = request.json

    name = data.get('name')
    dept_id = data.get('dept_id')
    dob = data.get('dob')
    address = data.get('address')
    designation = data.get('designation')
    manager_id = data.get('manager_id')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Employee
        SET DeptId=%s, Name=%s, Dob=%s, Address=%s, Designation=%s, ManagerId=%s
        WHERE Id=%s
    """, (dept_id, name, dob, address, designation, manager_id, id))

    conn.commit()

    return {"message": "Employee updated successfully"}

@app.route('/dashboard', methods=['GET'])
def dashboard():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Total Employees
    cursor.execute("SELECT COUNT(*) AS totalEmployees FROM Employee")
    totalEmployees = cursor.fetchone()['totalEmployees']

    # Total Departments
    cursor.execute("SELECT COUNT(*) AS totalDepartments FROM Department")
    totalDepartments = cursor.fetchone()['totalDepartments']

    # Employees Per Department
    cursor.execute("""
        SELECT d.Name, COUNT(e.Id) AS total
        FROM Department d
        LEFT JOIN Employee e ON d.id = e.DeptId
        GROUP BY d.Name
    """)

    employeesPerDept = cursor.fetchall()

    return jsonify({
        "totalEmployees": totalEmployees,
        "totalDepartments": totalDepartments,
        "employeesPerDept": employeesPerDept
    })

if __name__ == '__main__':
    app.run(debug=True)