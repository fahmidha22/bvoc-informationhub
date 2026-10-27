import re
from knowledge_base import DEPARTMENTS_KNOWLEDGE, BVOC_GENERAL_INFO

class BVocChatbotEngine:
    def __init__(self):
        self.departments = DEPARTMENTS_KNOWLEDGE
        self.general_info = BVOC_GENERAL_INFO

    def process_query(self, user_query: str) -> dict:
        query = user_query.strip().lower()
        
        # 1. Check for Greetings
        if any(word in query for word in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon"]):
            return {
                "answer": "Hello! Welcome to the **B.Voc Information Hub**. I am your AI Academic Advisor. How can I assist you today?",
                "quick_replies": [
                    "What is B.Voc?",
                    "List all 7 departments",
                    "Software Dev eligibility",
                    "Placement details"
                ]
            }

        # 2. Identify Department Entity
        dept_match = None
        dept_id_found = None
        
        for dept_id, info in self.departments.items():
            names_to_check = [
                dept_id,
                info["name"].lower(),
                info["short_name"].lower(),
                info["slug"].replace("-", " ")
            ]
            if dept_id == "software-dev":
                names_to_check.extend(["software", "system admin", "coding", "it", "devops", "cloud"])
            elif dept_id == "animation":
                names_to_check.extend(["animation", "graphic", "design", "vfx", "3d", "maya", "ui/ux"])
            elif dept_id == "fashion":
                names_to_check.extend(["fashion", "apparel", "textile", "garment", "modelling"])
            elif dept_id == "instrumentation":
                names_to_check.extend(["instrumentation", "automation", "plc", "scada", "robotics", "sensors"])
            elif dept_id == "logistics":
                names_to_check.extend(["logistics", "supply chain", "warehouse", "freight", "customs"])
            elif dept_id == "sports":
                names_to_check.extend(["sports", "fitness", "coaching", "gym", "athletic"])
            elif dept_id == "tourism":
                names_to_check.extend(["tourism", "travel", "hospitality", "hotel", "airline"])

            if any(term in query for term in names_to_check):
                dept_match = info
                dept_id_found = dept_id
                break

        # 3. Intent Detection: Syllabus
        if any(term in query for term in ["syllabus", "subjects", "modules", "curriculum", "course structure"]):
            if dept_match:
                syllabi_text = "\n".join([f"• **{sem}**: {subjects}" for sem, subjects in dept_match["syllabi_summary"].items()])
                return {
                    "answer": f"Here is the semester-wise syllabus overview for **{dept_match['name']}**:\n\n{syllabi_text}",
                    "quick_replies": [
                        f"Eligibility for {dept_match['short_name']}",
                        f"Placements for {dept_match['short_name']}",
                        f"Faculty of {dept_match['short_name']}"
                    ],
                    "department_ref": dept_match["slug"]
                }
            else:
                return {
                    "answer": "All 7 B.Voc departments follow a 6-semester NSQF-aligned structure. Which department syllabus would you like to inspect?\n\n1. Software Development\n2. Animation & Graphic Design\n3. Fashion Design\n4. Industrial Instrumentation\n5. Logistics Management\n6. Multi Sports & Fitness\n7. Tourism",
                    "quick_replies": [
                        "Tell me about Software Dev syllabus",
                        "Animation syllabus",
                        "Logistics syllabus"
                    ]
                }

        # 4. Intent Detection: Eligibility
        if any(term in query for term in ["eligibility", "qualification", "admission", "requirements", "marks", "cut off", "apply"]):
            if dept_match:
                return {
                    "answer": f"**Eligibility for {dept_match['name']}**:\n• {dept_match['eligibility']}\n\n**Duration**: {dept_match['duration']}\n• Flexible exit options at Diploma (Yr 1), Advanced Diploma (Yr 2), and B.Voc Degree (Yr 3).",
                    "quick_replies": [
                        f"Show syllabus for {dept_match['short_name']}",
                        f"Career paths in {dept_match['short_name']}",
                        "General B.Voc eligibility"
                    ],
                    "department_ref": dept_match["slug"]
                }
            else:
                return {
                    "answer": f"**General B.Voc Eligibility Criteria**:\n{self.general_info['eligibility_general']}\n\n*Note: Specializations like Industrial Instrumentation require 10+2 PCM or Diploma in Engineering.*",
                    "quick_replies": [
                        "Software Dev eligibility",
                        "Animation eligibility",
                        "Instrumentation eligibility"
                    ]
                }

        # 5. Intent Detection: Placements & Recruiters
        if any(term in query for term in ["placement", "recruiter", "package", "salary", "job", "career", "hiring", "company"]):
            if dept_match:
                recruiters_list = ", ".join(dept_match["top_recruiters"])
                roles_list = ", ".join(dept_match["career_roles"])
                return {
                    "answer": f"**Placement Highlights for {dept_match['name']}**:\n• **Average Package**: {dept_match['avg_package']}\n• **Career Roles**: {roles_list}\n• **Top Hiring Partners**: {recruiters_list}",
                    "quick_replies": [
                        f"Contact {dept_match['short_name']} HOD",
                        f"Syllabus for {dept_match['short_name']}",
                        "View all department placements"
                    ],
                    "department_ref": dept_match["slug"]
                }
            else:
                return {
                    "answer": "B.Voc programs maintain over **90%+ overall placement rate** across 50+ industry corporate partners including TCS, AWS, Siemens, DHL, Ubisoft, and MakeMyTrip.",
                    "quick_replies": [
                        "Software Dev placement",
                        "Animation placement",
                        "Logistics placement"
                    ]
                }

        # 6. Intent Detection: Faculty / HOD
        if any(term in query for term in ["faculty", "hod", "head", "professor", "teacher", "contact"]):
            if dept_match:
                return {
                    "answer": f"**Department Head & Contact ({dept_match['name']})**:\n• **HOD**: {dept_match['hod']}\n• **Email**: {dept_match['contact_email']}\n• **Phone**: {dept_match['contact_phone']}",
                    "quick_replies": [
                        f"Syllabus for {dept_match['short_name']}",
                        f"Eligibility for {dept_match['short_name']}"
                    ],
                    "department_ref": dept_match["slug"]
                }
            else:
                return {
                    "answer": "Our faculty comprises industry leaders, Ph.D. scholars, and certified domain experts across all 7 departments.",
                    "quick_replies": ["Software HOD", "Animation HOD", "Tourism HOD"]
                }

        # 7. Department Overview Query
        if dept_match:
            return {
                "answer": f"**{dept_match['name']}**\n*{dept_match['tagline']}*\n\n{dept_match['overview']}\n\n• **Duration**: {dept_match['duration']}\n• **Average Package**: {dept_match['avg_package']}",
                "quick_replies": [
                    f"Show syllabus for {dept_match['short_name']}",
                    f"Eligibility for {dept_match['short_name']}",
                    f"Placements for {dept_match['short_name']}"
                ],
                "department_ref": dept_match["slug"]
            }

        # 8. General What is B.Voc?
        if any(term in query for term in ["what is b.voc", "what is bvoc", "b.voc", "bvoc", "about b.voc", "bachelor of vocational"]):
            benefits_text = "\n".join([f"• {b}" for b in self.general_info["key_benefits"]])
            return {
                "answer": f"**{self.general_info['title']}**\n{self.general_info['overview']}\n\n**Key Highlights**:\n{benefits_text}",
                "quick_replies": [
                    "List all 7 departments",
                    "How to apply?",
                    "What are the exit points?"
                ]
            }

        # 9. List Departments
        if any(term in query for term in ["departments", "list departments", "specializations", "courses offered"]):
            depts_list = "\n".join([f"1. **{d['name']}** - {d['tagline']}" for d in self.departments.values()])
            return {
                "answer": f"We offer **7 Specialized B.Voc Degree Programs**:\n\n{depts_list}",
                "quick_replies": [
                    "Tell me about Software Dev",
                    "Tell me about Animation",
                    "Tell me about Tourism"
                ]
            }

        # Default Intelligent Fallback
        return {
            "answer": "I'm trained to help you with everything related to B.Voc programs! You can ask about:\n• Department Overviews\n• Semester Syllabi & Subjects\n• Eligibility & Admission Criteria\n• Placement Companies & Packages\n• Faculty & Contact Details",
            "quick_replies": [
                "What is B.Voc?",
                "List all 7 departments",
                "Placement Statistics"
            ]
        }
