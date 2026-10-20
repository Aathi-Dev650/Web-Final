# CropCure

CropCure AI is a Django-served React dashboard for farmer accounts, crop assessments, treatment guidance, and diagnosis history. User accounts use Django's local authentication database. MongoDB Atlas stores disease guidance and diagnosis results only; uploaded images are decoded in memory for the prediction request and are never saved.

## Run locally

1. Copy `.env.example` to `.env` and fill in `MONGODB_URI` with your MongoDB Atlas connection string. In Atlas, create a database user and allow your development IP address under **Network Access**. URL-encode special characters in the password.
2. Install dependencies: `venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Initialize Django accounts: `venv\Scripts\python.exe manage.py migrate`
4. Run the site: `venv\Scripts\python.exe manage.py runserver`
5. Open `http://127.0.0.1:8000/`.

## Train the MobileNetV2 disease model

The supplied PlantVillage subset has 15 classes: 12 diseases and 3 healthy-leaf classes across pepper, potato, and tomato. Its class folders can be trained directly; the trainer creates a deterministic 85/15 training/validation split. Run:

```powershell
venv\Scripts\python.exe ml\train.py --data-dir "dataset\PlantVillage" --epochs 3
```

The script uses ImageNet-pretrained MobileNetV2 and light image augmentation for three training epochs. It creates `ml/artifacts/disease_model.keras` and `class_names.json`, which the Django API loads automatically after server restart. Do not use the displayed confidence as a treatment recommendation; validate the model with representative local field images first.

## API

- `POST /api/disease/auth/register/` and `POST /api/disease/auth/login/`
- `POST /api/disease/create/` (authenticated multipart upload; the image is not persisted)
- `GET /api/disease/history/` (authenticated)

## Seed disease guidance

After configuring MongoDB, add the reviewed starter guidance with:

```powershell
venv\Scripts\python.exe manage.py seed_disease_guidance
```

The model supplies the crop/disease class only. Symptoms, recommended solution, and prevention are read from MongoDB's `diseases` collection. Add guidance for every class in your trained model before presenting it to users.

CSRF session protection is enabled for browser mutations. Do not commit `.env` or Atlas credentials.
