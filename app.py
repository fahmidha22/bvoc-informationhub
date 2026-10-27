import os

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

import firebase_admin
from firebase_admin import credentials, firestore, auth

from chatbot_engine import BVocChatbotEngine


# =====================================================
# BASE DIRECTORY
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =====================================================
# FLASK APP
# =====================================================

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates")
)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "bvoc-information-hub-development-key"
)


# =====================================================
# FIREBASE CONNECTION
# =====================================================

service_account_path = os.path.join(
    BASE_DIR,
    "serviceAccountKey.json"
)

if not firebase_admin._apps:

    cred = credentials.Certificate(
        service_account_path
    )

    firebase_admin.initialize_app(cred)


db = firestore.client()


# =====================================================
# CHATBOT
# =====================================================

chatbot = BVocChatbotEngine()


# =====================================================
# ADMIN PERMISSION HELPERS
# =====================================================

def get_current_user():
    """
    Get the currently logged-in user's Firestore data.
    Returns None if the user is not logged in or
    the user does not exist in Firestore.
    """

    if "user" not in session:
        return None

    uid = session["user"]["uid"]

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return None

    user_data = user_doc.to_dict()

    # Add Firebase UID to the user data
    user_data["uid"] = uid

    return user_data


def can_manage_department(user_data, department_id):
    """
    Check whether the logged-in user can manage
    the requested department.

    Super Admin:
        role = "admin"
        Can manage all departments.

    Department Admin:
        role = "department_admin"
        Can manage only the department whose ID
        matches their departmentId.
    """

    if not user_data:
        return False

    role = user_data.get("role")

    # Super Admin can manage everything
    if role == "admin":
        return True

    # Department Admin can manage only their department
    if role == "department_admin":

        user_department_id = str(
            user_data.get("departmentId", "")
        )

        requested_department_id = str(
            department_id
        )

        return (
            user_department_id ==
            requested_department_id
        )

    return False


# =====================================================
# GET DEPARTMENTS FROM FIRESTORE
# =====================================================

def get_departments():

    departments_ref = db.collection("departments")

    departments_docs = departments_ref.stream()

    departments_list = []

    for doc in departments_docs:

        department = doc.to_dict()

        # Add Firebase document ID
        department["id"] = doc.id

        departments_list.append(department)

    return departments_list


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():

    departments_list = get_departments()

    return render_template(
        "index.html",
        departments=departments_list
    )


# =====================================================
# DEPARTMENTS PAGE
# =====================================================

@app.route("/departments")
def departments():

    departments_list = get_departments()

    return render_template(
        "departments.html",
        departments=departments_list
    )


# =====================================================
# INDIVIDUAL DEPARTMENT DETAILS
# =====================================================

@app.route("/departments/<department_id>")
def department_detail(department_id):

    department_ref = (
        db.collection("departments")
        .document(department_id)
    )

    department_doc = department_ref.get()

    if not department_doc.exists:

        return "Department not found", 404

    
    department = department_doc.to_dict()

    # Add Firebase document ID
    department["id"] = department_doc.id

    return render_template(
        "department_detail.html",
        department=department
    )



# SOFTWARE DEVELOPMENT FACULTY
@app.route("/departments/1/faculty")
def software_faculty():

    department_ref = (
        db.collection("departments")
        .document("1")
    )

    department_doc = department_ref.get()

    if not department_doc.exists:
        return "Department not found", 404

    department = department_doc.to_dict()

    faculty_members = department.get("faculty", [])

    return render_template(
        "software_faculty.html",
        faculty=faculty_members
    )
    
# INDIVIDUAL SOFTWARE FACULTY DETAILS
@app.route("/departments/1/faculty/<faculty_id>")
def software_faculty_detail(faculty_id):

    department_ref = (
        db.collection("departments")
        .document("1")
    )

    department_doc = department_ref.get()

    if not department_doc.exists:
        return "Department not found", 404

    department = department_doc.to_dict()
    faculty_members = department.get("faculty", [])

    faculty_member = next(
        (
            member for member in faculty_members
            if str(member.get("id", "")) == str(faculty_id)
        ),
        None
    )

    if faculty_member is None:
        return "Faculty member not found", 404

    return render_template(
        "software_faculty_detail.html",
        faculty=faculty_member
    )




# =====================================================
# CHATBOT API
# =====================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json()

    if not data or "message" not in data:

        return jsonify({
            "answer": "Please enter a message."
        }), 400

    user_message = data["message"]

    response = chatbot.process_query(
        user_message
    )

    return jsonify(response)


# =====================================================
# AUTHENTICATION PAGES
# =====================================================

@app.route("/login")
def login_page():
    login_type = request.args.get("type", "student")

    if login_type not in ["student", "admin"]:
        login_type = "student"

    return render_template(
        "login.html",
        login_type=login_type
    )


@app.route("/signup")
def signup_page():

    if "user" in session:

        return redirect(
            url_for("home")
        )

    return render_template(
        "signup.html"
    )
# =====================================================
# FIREBASE LOGIN SESSION
# =====================================================

@app.route("/auth/session", methods=["POST"])
def create_session():

    data = request.get_json()

    if not data or "idToken" not in data:
        return jsonify({
            "success": False,
            "message": "Authentication token missing."
        }), 400

    try:

        id_token = data["idToken"]

        # Verify Firebase ID token
        decoded_token = auth.verify_id_token(id_token)

        uid = decoded_token["uid"]

        email = decoded_token.get(
            "email",
            ""
        )

        # Get user's Firestore document
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                "success": False,
                "message": "User profile not found."
            }), 404

        user_data = user_doc.to_dict()

        role = user_data.get(
            "role",
            "student"
        )

        department_id = user_data.get(
            "departmentId"
        )

        # =================================================
        # RECORD LOGIN ACTIVITY
        # =================================================

        # Update user's login information
        user_ref.update({
            "lastLoginAt": firestore.SERVER_TIMESTAMP,
            "loginCount": firestore.Increment(1)
        })

        # Create a login activity record
        db.collection("login_activity").add({
            "uid": uid,
            "email": email,
            "role": role,
            "departmentId": department_id,
            "loginTime": firestore.SERVER_TIMESTAMP
        })

        # =================================================
        # CREATE FLASK SESSION
        # =================================================

        session["user"] = {
            "uid": uid,
            "email": email,
            "role": role,
            "departmentId": department_id
        }

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "role": role,
            "departmentId": department_id
        })

    except Exception as e:

        print(
            "Authentication error:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Authentication failed."
        }), 401


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )



# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin")
def admin_dashboard():

    # Check if user is logged in
    if "user" not in session:
        return redirect(
            url_for("login_page", type="admin")
        )


    # Get current logged-in user
    user_data = get_current_user()


    # User profile not found
    if not user_data:

        session.clear()

        return redirect(
            url_for("login_page", type="admin")
        )


    # Get role
    role = user_data.get("role")


    # =================================================
    # SUPER ADMIN
    # =================================================

    if role == "admin":

        # Super Admin can see all departments
        departments = get_departments()

        # Super Admin can see all users
        users_ref = db.collection("users")

        users_docs = users_ref.stream()

        users = []

        for doc in users_docs:

            user = doc.to_dict()

            user["id"] = doc.id

            users.append(user)


    # =================================================
    # DEPARTMENT ADMIN
    # =================================================

    elif role == "department_admin":

        department_id = user_data.get(
            "departmentId"
        )


        # Department not assigned
        if not department_id:

            return (
                "Your account is not assigned to a department.",
                403
            )


        # Get only assigned department
        all_departments = get_departments()

        departments = [
            dept
            for dept in all_departments
            if str(dept.get("id"))
            == str(department_id)
        ]


        # Department doesn't exist
        if not departments:

            return (
                "Your assigned department was not found.",
                404
            )


        # Department admins don't need
        # the complete user list
        users = []


    # =================================================
    # INVALID ROLE
    # =================================================

    else:

        return "Access denied.", 403


    # =================================================
    # OPEN DASHBOARD
    # =================================================

    return render_template(
        "admin.html",
        user=user_data,
        users=users,
        departments=departments
    )

# EDIT FACULTY
@app.route("/admin/faculty/edit/<department_id>", methods=["GET", "POST"])
def edit_faculty(department_id):

    user_data = get_current_user()

    if not user_data:
        return redirect(url_for("login_page", type="admin"))

    if not can_manage_department(user_data, department_id):
        return "Access denied. You can only manage your own department.", 403

    department_ref = db.collection("departments").document(department_id)
    department_doc = department_ref.get()

    if not department_doc.exists:
        return "Department not found.", 404

    department = department_doc.to_dict()
    department["id"] = department_id

    faculty = department.get("faculty", [])

    if request.method == "POST":

        names = request.form.getlist("faculty_name")
        experiences = request.form.getlist("faculty_experience")
        images = request.form.getlist("faculty_image")
        emails = request.form.getlist("faculty_email")
        ids = request.form.getlist("faculty_id")
        designations = request.form.getlist("faculty_designation")
        qualifications = request.form.getlist("faculty_qualification")
        specializations = request.form.getlist("faculty_specialization")

        updated_faculty = []

        for i in range(len(names)):

            name = names[i].strip()

            # Ignore completely empty faculty rows
            if not name:
                continue

            member = {
                "name": name,
                "experience": experiences[i].strip() if i < len(experiences) else "",
                "image": images[i].strip() if i < len(images) else "",
                "email": emails[i].strip() if i < len(emails) else "",
                "id": ids[i].strip() if i < len(ids) else "",
                "designation": designations[i].strip() if i < len(designations) else "",
                "qualification": qualifications[i].strip() if i < len(qualifications) else "",
                "specialization": specializations[i].strip() if i < len(specializations) else ""
            }

            updated_faculty.append(member)

        department_ref.update({
            "faculty": updated_faculty
        })

        return redirect(url_for("admin_faculty"))

    return render_template(
        "edit_faculty.html",
        department=department,
        faculty=faculty,
        user=user_data
    )
# =====================================================
# PLACEMENTS MANAGEMENT
# =====================================================

@app.route("/admin/placements")
def admin_placements():

    user_data = get_current_user()

    if not user_data:
        return redirect(
            url_for("login_page", type="admin")
        )

    role = user_data.get("role")


    # =================================================
    # SUPER ADMIN
    # =================================================

    if role == "admin":

        departments = get_departments()


    # =================================================
    # DEPARTMENT ADMIN
    # =================================================

    elif role == "department_admin":

        department_id = user_data.get(
            "departmentId"
        )

        if not department_id:
            return (
                "Your account is not assigned to a department.",
                403
            )

        all_departments = get_departments()

        departments = [
            dept
            for dept in all_departments
            if str(dept.get("id"))
            == str(department_id)
        ]

        if not departments:
            return (
                "Your assigned department was not found.",
                404
            )


    # =================================================
    # INVALID ROLE
    # =================================================

    else:

        return "Access denied.", 403


    return render_template(
        "admin_placements.html",
        departments=departments,
        user=user_data
    )
# =====================================================
# ACHIEVEMENTS MANAGEMENT
# =====================================================

@app.route("/admin/achievements")
def admin_achievements():

    user_data = get_current_user()

    if not user_data:
        return redirect(
            url_for("login_page", type="admin")
        )

    role = user_data.get("role")


    # =================================================
    # SUPER ADMIN
    # =================================================

    if role == "admin":

        departments = get_departments()


    # =================================================
    # DEPARTMENT ADMIN
    # =================================================

    elif role == "department_admin":

        department_id = user_data.get(
            "departmentId"
        )

        if not department_id:
            return (
                "Your account is not assigned to a department.",
                403
            )

        all_departments = get_departments()

        departments = [
            dept
            for dept in all_departments
            if str(dept.get("id"))
            == str(department_id)
        ]

        if not departments:
            return (
                "Your assigned department was not found.",
                404
            )


    # =================================================
    # INVALID ROLE
    # =================================================

    else:

        return "Access denied.", 403


    return render_template(
        "admin_achievements.html",
        departments=departments,
        user=user_data
    )


# =====================================================
# EDIT ACHIEVEMENTS
# =====================================================

@app.route(
    "/admin/achievements/edit/<department_id>",
    methods=["GET", "POST"]
)
def edit_achievements(department_id):

    user_data = get_current_user()

    if not user_data:
        return redirect(
            url_for("login_page", type="admin")
        )


    # =================================================
    # SECURITY CHECK
    # =================================================

    if not can_manage_department(
        user_data,
        department_id
    ):

        return (
            "Access denied. You can only manage your own department.",
            403
        )


    # =================================================
    # GET DEPARTMENT
    # =================================================

    department_ref = (
        db.collection("departments")
        .document(department_id)
    )

    department_doc = department_ref.get()


    if not department_doc.exists:

        return (
            "Department not found.",
            404
        )


    department = department_doc.to_dict()

    department["id"] = department_id


    # Existing achievements

    achievements = department.get(
        "achievements",
        []
    )


    # =================================================
    # SAVE ACHIEVEMENTS
    # =================================================

    if request.method == "POST":

        titles = request.form.getlist(
            "achievement_title"
        )

        categories = request.form.getlist(
            "achievement_category"
        )

        years = request.form.getlist(
            "achievement_year"
        )

        badges = request.form.getlist(
            "achievement_badge"
        )

        students = request.form.getlist(
            "achievement_student"
        )

        descriptions = request.form.getlist(
            "achievement_description"
        )


        updated_achievements = []


        for i in range(len(titles)):

            title = titles[i].strip()


            # Ignore empty achievement rows

            if not title:
                continue


            achievement = {

                "title": title,

                "category":
                    categories[i].strip()
                    if i < len(categories)
                    else "",

                "year":
                    years[i].strip()
                    if i < len(years)
                    else "",

                "badge":
                    badges[i].strip()
                    if i < len(badges)
                    else "",

                "studentName":
                    students[i].strip()
                    if i < len(students)
                    else "",

                "description":
                    descriptions[i].strip()
                    if i < len(descriptions)
                    else ""
            }


            updated_achievements.append(
                achievement
            )


        # Save only to the authorized department

        department_ref.update({

            "achievements":
                updated_achievements

        })


        return redirect(
            url_for("admin_achievements")
        )


    # =================================================
    # EDIT PAGE
    # =================================================

    return render_template(
        "edit_achievements.html",

        department=department,

        achievements=achievements,

        user=user_data
    )
# =====================================================
# EDIT PLACEMENTS
# =====================================================

@app.route(
    "/admin/placements/edit/<department_id>",
    methods=["GET", "POST"]
)
def edit_placements(department_id):

    user_data = get_current_user()

    if not user_data:
        return redirect(
            url_for("login_page", type="admin")
        )


    # =================================================
    # SECURITY CHECK
    # =================================================

    if not can_manage_department(
        user_data,
        department_id
    ):

        return (
            "Access denied. You can only manage your own department.",
            403
        )


    # =================================================
    # GET DEPARTMENT
    # =================================================

    department_ref = (
        db.collection("departments")
        .document(department_id)
    )

    department_doc = department_ref.get()


    if not department_doc.exists:

        return (
            "Department not found.",
            404
        )


    department = department_doc.to_dict()

    department["id"] = department_id


    # Existing placement data

    placements = department.get(
        "placements",
        {}
    )


    # =================================================
    # SAVE PLACEMENT INFORMATION
    # =================================================

    if request.method == "POST":


        # =============================================
        # PLACEMENT STATISTICS
        # =============================================

        average_package = request.form.get(
            "averagePackage",
            ""
        ).strip()


        highest_package = request.form.get(
            "highestPackage",
            ""
        ).strip()


        placement_rate = request.form.get(
            "placementRate",
            ""
        ).strip()


        # =============================================
        # INTERNSHIP PARTNERS
        # =============================================

        internship_partners = []


        partners = request.form.getlist(
            "internship_partner"
        )


        for partner in partners:

            partner = partner.strip()

            if partner:

                internship_partners.append(
                    partner
                )


        # =============================================
        # RECRUITERS
        # =============================================

        recruiter_names = request.form.getlist(
            "recruiter_name"
        )


        recruiter_logo_texts = request.form.getlist(
            "recruiter_logoText"
        )


        recruiter_logo_colors = request.form.getlist(
            "recruiter_logoColor"
        )


        recruiters = []


        for i in range(
            len(recruiter_names)
        ):

            name = recruiter_names[i].strip()


            if not name:
                continue


            # Recruiter logo text

            logo_text = ""

            if i < len(
                recruiter_logo_texts
            ):

                logo_text = (
                    recruiter_logo_texts[i]
                    .strip()
                )


            # Recruiter logo color

            logo_color = ""

            if i < len(
                recruiter_logo_colors
            ):

                logo_color = (
                    recruiter_logo_colors[i]
                    .strip()
                )


            # =========================================
            # JOB ROLES FOR THIS RECRUITER
            # =========================================

            roles = request.form.getlist(
                f"recruiter_role_{i}"
            )


            roles = [
                role.strip()
                for role in roles
                if role.strip()
            ]


            recruiter = {

                "name": name,

                "logoText": logo_text,

                "logoColor": logo_color,

                "roles": roles

            }


            recruiters.append(
                recruiter
            )


        # =============================================
        # UPDATED PLACEMENT OBJECT
        # =============================================

        updated_placements = {

            "averagePackage":
                average_package,

            "highestPackage":
                highest_package,

            "placementRate":
                placement_rate,

            "internshipPartners":
                internship_partners,

            "recruiters":
                recruiters

        }


        # =============================================
        # SAVE TO FIRESTORE
        # =============================================

        department_ref.update({

            "placements":
                updated_placements

        })


        # =============================================
        # RETURN TO PLACEMENTS PAGE
        # =============================================

        return redirect(
            url_for(
                "admin_placements"
            )
        )


    # =================================================
    # DISPLAY EDIT PAGE
    # =================================================

    return render_template(

        "edit_placements.html",

        department=department,

        placements=placements,

        user=user_data

    )

# =====================================================
# DEBUG STATIC FILES
# =====================================================

@app.route("/debug-static")
def debug_static():

    css_path = os.path.join(
        app.static_folder,
        "css",
        "style.css"
    )

    return f"""
    <h2>Static Folder Test</h2>

    <p>
        <b>Static folder:</b>
        {app.static_folder}
    </p>

    <p>
        <b>CSS path:</b>
        {css_path}
    </p>

    <p>
        <b>CSS exists:</b>
        {os.path.exists(css_path)}
    </p>

    <p>
        <b>CSS URL:</b>
        <a href="/static/css/style.css">
            /static/css/style.css
        </a>
    </p>
    """

     # =====================================================
# ADMIN DEPARTMENTS
# =====================================================

@app.route("/admin/departments")
def admin_departments():

    if "user" not in session:
        return redirect(url_for("login_page"))

    uid = session["user"]["uid"]

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        session.clear()
        return redirect(url_for("login_page"))

    user_data = user_doc.to_dict()

    if user_data.get("role") != "admin":
        return "Access denied. Admins only.", 403

    departments_list = get_departments()

    return render_template(
        "admin_departments.html",
        departments=departments_list,
        user=user_data
    )
# =====================================================
# EDIT DEPARTMENT
# =====================================================

@app.route("/admin/departments/edit/<department_id>", methods=["GET", "POST"])
def edit_department(department_id):

    # Check login
    if "user" not in session:
        return redirect(url_for("login_page"))

    # Get logged-in user's UID
    uid = session["user"]["uid"]

    # Check user in Firestore
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        session.clear()
        return redirect(url_for("login_page"))

    user_data = user_doc.to_dict()

    # Check admin role
    if user_data.get("role") != "admin":
        return "Access denied. Admins only.", 403

    # Get department
    department_ref = (
        db.collection("departments")
        .document(department_id)
    )

    department_doc = department_ref.get()

    if not department_doc.exists:
        return "Department not found.", 404

    department = department_doc.to_dict()

    department["id"] = department_id

    # Save changes
    if request.method == "POST":

        updated_data = {

            "name": request.form.get(
                "name",
                ""
            ).strip(),

            "shortCode": request.form.get(
                "shortCode",
                ""
            ).strip(),

            "tagline": request.form.get(
                "tagline",
                ""
            ).strip(),

            "shortDescription": request.form.get(
                "shortDescription",
                ""
            ).strip(),

            "fullOverview": request.form.get(
                "fullOverview",
                ""
            ).strip(),

            "eligibility": request.form.get(
                "eligibility",
                ""
            ).strip(),

            "duration": request.form.get(
                "duration",
                ""
            ).strip()
        }

        # Update Firestore
        department_ref.update(updated_data)

        # Go back to departments
        return redirect(
            url_for("admin_departments")
        )

    # Display edit form
    return render_template(
        "edit_department.html",
        department=department,
        user=user_data
    )




# =====================================================
# START FLASK
# =====================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )