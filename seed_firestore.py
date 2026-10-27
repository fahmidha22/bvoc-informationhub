import os
import json5

import firebase_admin
from firebase_admin import credentials, firestore


# ---------------------------------------
# Paths
# ---------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        "src",
        "data",
        "bvocData.ts"
    )
)

SERVICE_ACCOUNT = os.path.join(
    BASE_DIR,
    "serviceAccountKey.json"
)


# ---------------------------------------
# Check files
# ---------------------------------------

print("Looking for:")
print(DATA_FILE)

if not os.path.exists(DATA_FILE):
    print("\nERROR: bvocData.ts was not found.")
    exit()

if not os.path.exists(SERVICE_ACCOUNT):
    print("\nERROR: serviceAccountKey.json was not found.")
    exit()


# ---------------------------------------
# Read bvocData.ts
# ---------------------------------------

with open(DATA_FILE, "r", encoding="utf-8") as file:
    content = file.read()


# ---------------------------------------
# Find BVOC_DEPARTMENTS
# ---------------------------------------

start = content.find("export const BVOC_DEPARTMENTS")

if start == -1:
    print("\nERROR: BVOC_DEPARTMENTS was not found.")
    exit()


# IMPORTANT:
# Find the "=" first, then find the "[".
# This avoids accidentally selecting
# the [] in Department[].
equal_sign = content.find("=", start)

array_start = content.find("[", equal_sign)

if equal_sign == -1 or array_start == -1:
    print("\nERROR: Department array could not be found.")
    exit()


# ---------------------------------------
# Find the matching closing ]
# ---------------------------------------

level = 0
quote = None
escape = False
array_end = None

for i in range(array_start, len(content)):

    character = content[i]

    if quote:

        if escape:
            escape = False

        elif character == "\\":
            escape = True

        elif character == quote:
            quote = None

    else:

        if character in ("'", '"'):
            quote = character

        elif character == "[":
            level += 1

        elif character == "]":
            level -= 1

            if level == 0:
                array_end = i
                break


if array_end is None:
    print("\nERROR: Could not find the end of department data.")
    exit()


departments_text = content[
    array_start:array_end + 1
]


# ---------------------------------------
# Convert TypeScript-style data
# ---------------------------------------

try:
    departments = json5.loads(departments_text)

except Exception as error:
    print("\nERROR while reading department data:")
    print(error)
    exit()


print("\nDepartments found:", len(departments))


# ---------------------------------------
# Connect to Firebase
# ---------------------------------------

cred = credentials.Certificate(SERVICE_ACCOUNT)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------------------------------
# Upload departments
# ---------------------------------------

print("\nUploading departments...\n")

for department in departments:

    department_id = str(department["id"])

    db.collection("departments").document(
        department_id
    ).set(department)

    print(
        "Uploaded:",
        department["name"]
    )


# ---------------------------------------
# Finished
# ---------------------------------------

print("\n--------------------------------")
print("SUCCESS!")
print("--------------------------------")
print("All departments were uploaded to Firestore.")