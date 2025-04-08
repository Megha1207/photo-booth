import torch
import numpy as np
from PIL import Image
from facenet_pytorch import InceptionResnetV1, MTCNN
from torchvision import transforms
from app.config import Config

# Load model once on module load
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = InceptionResnetV1(pretrained=None).to(device)
model.load_state_dict(torch.load(Config.MODEL_PATH, map_location=device), strict=False)
model.eval()

# Initialize MTCNN for face detection
mtcnn = MTCNN(keep_all=True, device=device)

# Transform for resizing and normalization
face_transform = transforms.Compose([
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize([0.5], [0.5])
])

def extract_embeddings(image: Image.Image) -> list:
    """Extract face embeddings from a PIL Image object."""
    try:
        image = image.convert("RGB")
        boxes, _ = mtcnn.detect(image)

        if boxes is None:
            return []

        embeddings = []
        for (x1, y1, x2, y2) in boxes:
            cropped_face = image.crop((int(x1), int(y1), int(x2), int(y2)))
            tensor = face_transform(cropped_face).unsqueeze(0).to(device)
            with torch.no_grad():
                embedding = model(tensor).cpu().numpy().flatten()
            embeddings.append(embedding.tolist())

        return embeddings
    except Exception as e:
        print(f"[Embedding Extraction Error] {e}")
        return []

def compare_embeddings(embedding1: list, embedding2: list, threshold: float = 0.6) -> bool:
    """Compare two embeddings and return True if they match within threshold."""
    if not embedding1 or not embedding2:
        return False
    distance = np.linalg.norm(np.array(embedding1) - np.array(embedding2))
    return distance < threshold
