import streamlit as st
import requests
from PIL import Image
import io
import base64


API_URL = "http://localhost:8000"

# --- Session State Initialization ---
if "token" not in st.session_state:
    st.session_state.token = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

st.set_page_config(page_title="Photobooth Face Recognition", layout="centered")
st.title("📸 Photobooth Face Recognition App")

# --- Register ---
with st.expander("📝 Register"):
    reg_name = st.text_input("Name", key="reg_name")
    reg_email = st.text_input("Email", key="reg_email")
    reg_pass = st.text_input("Password", type="password", key="reg_pass")
    reg_btn = st.button("Register")

    if reg_btn:
        response = requests.post(
            f"{API_URL}/api/register",
            data={
                "user_name": reg_name,
                "email": reg_email,
                "password": reg_pass
            }
        )
        if response.status_code == 200:
            st.success("Registration successful. You can now log in.")
        else:
            st.error(f"Registration failed: {response.text}")

# --- Login ---
with st.expander("🔐 Login"):
    login_email = st.text_input("Email", key="login_email")
    login_pass = st.text_input("Password", type="password", key="login_pass")
    login_btn = st.button("Login")

    if login_btn:
        response = requests.post(
            f"{API_URL}/api/login",
            data={"username": login_email, "password": login_pass}
        )
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.token = token_data["access_token"]
            st.session_state.user_name = token_data.get("user_name", login_email)
            st.session_state.user_id = token_data.get("user_id")
            st.success("Login successful!")
        else:
            st.error(f"Login failed: {response.text}")

# --- Auth Header Helper ---
def get_auth_headers():
    token = st.session_state.get("token")
    if not token:
        st.warning("Please log in first.")
        return None
    return {"Authorization": f"Bearer {token}"}

# --- Upload Event Files ---
st.header("📁 Upload Event Files")
event_id = st.text_input("Enter Event ID")
event_files = st.file_uploader("Select Event Images", type=["jpg", "jpeg", "png", "jfif", "heic" ], accept_multiple_files=True)

if st.button("Upload Event Files"):
    headers = get_auth_headers()
    if not headers:
        st.stop()
    if not event_id or not event_files:
        st.warning("Provide Event ID and files.")
    else:
        for file in event_files:
            response = requests.post(
                f"{API_URL}/api/upload/file",
                headers=headers,
                files={"file": (file.name, file.getvalue())},
                data={
                    "event_id": event_id,
                    "user_id": st.session_state.user_id
                }
            )
            if response.status_code == 200:
                st.success(f"Uploaded: {file.name}")
            else:
                st.error(f"Failed: {file.name} — {response.text}")

# --- Face Match ---
st.header("🔍 Search by Face")
search_event_id = st.text_input("Search in Event ID")
face_file = st.file_uploader("Upload Face Image", type=["jpg", "jpeg", "png", "heic","jfif"], key="search_face")

if st.button("Search Matches"):
    headers = get_auth_headers()
    if not headers:
        st.stop()
    if not face_file or not search_event_id:
        st.warning("Provide event ID and face image.")
    elif not st.session_state.user_id:
        st.warning("User ID missing. Log in again.")
    else:
        # Step 1: Upload the face
        response = requests.post(
            f"{API_URL}/api/upload/face",
            files={"face": (face_file.name, face_file.getvalue())},
            data={
                "event_id": search_event_id,
                "user_id": st.session_state.user_id
            },
            headers=headers
        )

        if response.status_code == 200 and "face_id" in response.json():
            face_id = response.json()["face_id"]
            st.success("Face uploaded. Searching for matches...")

            # Step 2: Match the face (return all matches as base64)
            match_response = requests.post(
                f"{API_URL}/api/match-face",
                data={"face_id": face_id, "event_id": search_event_id},
                headers=headers
            )

            if match_response.status_code == 200:
                matched_data = match_response.json()
                matched_images = matched_data.get("matched_images", [])

                st.image(face_file, caption="Uploaded Face", width=300)

                if matched_images:
                    st.subheader("🎯 Matched Images:")
                    for i, item in enumerate(matched_images):
                       img_bytes = base64.b64decode(item["image_base64"])
                       matched_img = Image.open(io.BytesIO(img_bytes))

                       st.image(matched_img, caption=f"Match #{i+1} (Similarity: {item['similarity']:.2f})", use_column_width=True)

                       # Prepare download
                       img_buffer = io.BytesIO()
                       matched_img.save(img_buffer, format="JPEG")
                       img_buffer.seek(0)

                       st.download_button(
                       label=f"📥 Download Match #{i+1}",
                       data=img_buffer,
                       file_name=f"match_{i+1}.jpg",
                       mime="image/jpeg"
    )

                else:
                    st.info("No matching faces found.")
            else:
                st.error(f"No match found. {match_response.text}")
        else:
            st.error("Failed to upload face.")



# --- Check Duplicates ---
st.header("♻️ Check Duplicates")
if st.button("Check for Duplicates"):
    headers = get_auth_headers()
    if not headers:
        st.stop()
    response = requests.get(f"{API_URL}/api/duplicates/", headers=headers)
    if response.status_code == 200:
        duplicates = response.json().get("duplicates", [])
        if duplicates:
            st.write(f"Found {len(duplicates)} duplicates:")
            for dup in duplicates:
                st.write(dup)
            if st.button("Delete Duplicates"):
                file_ids = [dup["file_id"] for dup in duplicates]
                del_response = requests.delete(
                    f"{API_URL}/api/duplicates/",
                    json={"file_ids": file_ids},
                    headers=headers
                )
                if del_response.status_code == 200:
                    st.success("Duplicates deleted.")
                else:
                    st.error("Failed to delete.")
        else:
            st.info("No duplicates found.")
    else:
        st.error("Error checking duplicates.")


