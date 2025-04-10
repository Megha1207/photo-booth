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

# --- Sidebar Navigation ---
st.set_page_config(page_title="Photobooth", layout="centered")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a Page", ["Home", "Authentication", "Event Management", "Face Recognition", "Public Viewer", "Gallery"])

# --- Home Page ---
if page == "Home":
    st.title("PhotoBooth📸")
    
    # Introductory text
    st.write(
        """
        Use the sidebar to navigate through the app. Happy organizing!
        """
    )

    # Add navigation button to prompt users to login or register
    st.write("New to the app? Please [Register](#) or [Log in](#) to get started!")

# --- Auth Header Helper ---
def get_auth_headers():
    token = st.session_state.get("token")
    if not token:
        st.warning("Please log in first.")
        return None
    return {"Authorization": f"Bearer {token}"}

# --- Authentication Page ---
if page == "Authentication":
    st.title("📸 Photobooth Face Recognition App")
    
    # Register
    if not st.session_state.token:
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
    
    # Login
    if not st.session_state.token:
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
    
    # Logout Button
    if st.session_state.token:
        if st.button("🚪 Logout"):
            st.session_state.token = None
            st.session_state.user_name = None
            st.session_state.user_id = None
            st.success("Logged out successfully.")

# --- Event Management Page ---
elif page == "Event Management" and st.session_state.token:
    st.title("📂 Event Management")
    
    # Upload Event Files
    st.header("📁 Upload Event Files")
    event_id = st.text_input("Enter Event ID")
    event_files = st.file_uploader(
        "Select Event Images", 
        type=["jpg", "jpeg", "png", "jfif", "heic"],
        accept_multiple_files=True
    )

    if st.button("Upload Event Files"):
        headers = get_auth_headers()
        if not headers:
            st.stop()

        if not event_id:
            st.warning("Please enter an Event ID.")
        elif not event_files:
            st.warning("Please select at least one file.")
        else:
            progress = st.progress(0)
            uploaded_count = 0

            for i, file in enumerate(event_files):
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
                    st.success(f"✅ Uploaded: {file.name}")
                    uploaded_count += 1
                else:
                    st.error(f"❌ Failed: {file.name} — {response.text}")

                progress.progress((i + 1) / len(event_files))

            if uploaded_count > 0:
                st.success(f"🎉 {uploaded_count} file(s) uploaded successfully.")

    # Check Duplicates
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

    # View Event Files
    st.header("📂 View Uploaded Event Files (Private)")
    view_event_id = st.text_input("Enter Event ID to View Files", key="view_event")

    if st.button("Fetch Event Files"):
        headers = get_auth_headers()
        if not headers:
            st.stop()

        if not view_event_id:
            st.warning("Please enter an Event ID.")
        else:
            response = requests.get(f"{API_URL}/api/event/{view_event_id}/files", headers=headers)

            if response.status_code == 200:
                files = response.json().get("files", [])
                if files:
                    st.success(f"Found {len(files)} files for Event ID: {view_event_id}")
                    col_count = 3  # Number of columns for the gallery layout
                    cols = st.columns(col_count)
                    for i, file in enumerate(files):
                        file_url = f"{API_URL}/files/{file['filename']}"
                        col_idx = i % col_count
                        with cols[col_idx]:
                            st.image(file_url, caption=f"Image #{i+1}: {file['filename']}", use_column_width=True)

                            st.markdown(
                                f"[📥 Download {file['filename']}]({file_url})",
                                unsafe_allow_html=True
                            )
                else:
                    st.info("No files found for this event.")
            else:
                st.error(f"Failed to fetch files: {response.text}")

# --- Face Recognition Page ---
elif page == "Face Recognition" and st.session_state.token:
    st.title("🔍 Face Recognition")
    
    # Search Face
    search_event_id = st.text_input("Search in Event ID")
    face_file = st.file_uploader("Upload Face Image", type=["jpg", "jpeg", "png", "heic", "jfif"], key="search_face")

    if st.button("Search Matches"):
        headers = get_auth_headers()
        if not headers:
            st.stop()
        if not face_file or not search_event_id:
            st.warning("Provide event ID and face image.")
        elif not st.session_state.user_id:
            st.warning("User ID missing. Log in again.")
        else:
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

# --- Public Event Viewer Page ---
elif page == "Public Viewer":
    st.title("🌍 Public Event Viewer")
    
    public_event_id = st.text_input("Enter Event ID to View Images (Public)", key="public_event")

    if st.button("View Images (Public)"):
        response = requests.get(f"{API_URL}/api/event/{public_event_id}/files")
        if response.status_code == 200:
            files = response.json().get("files", [])
            if files:
                st.success(f"📸 Found {len(files)} files for Event ID: {public_event_id}")
                for i, file in enumerate(files):
                    file_url = f"{API_URL}/files/{file['filename']}"
                    st.image(file_url, caption=f"Image #{i+1}: {file['filename']}", use_column_width=True)

                    st.markdown(
                        f"[📥 Download {file['filename']}]({file_url})",
                        unsafe_allow_html=True
                    )
            else:
                st.info("No public files found for this event.")
        else:
            st.error(f"Failed to fetch files: {response.text}")
