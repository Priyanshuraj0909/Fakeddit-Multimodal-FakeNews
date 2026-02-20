📰 Fakeddit Multimodal Fake News Detection (fakeddit_models)
This project develops and compares multiple deep learning models for multimodal fake news detection using the Fakeddit dataset, which contains both text and image modalities.

The work explores a range of architectures — from traditional CNN-LSTM fusion to OpenAI’s CLIP — and evaluates different fusion strategies to achieve the best possible accuracy.

The best configuration achieved 93.9% accuracy, using CLIP (ViT-B/32) embeddings combined with other metadata and an XGBoost classifier.

📚 Overview
The project was developed entirely in Google Colab using .ipynb notebooks.
Each notebook represents a key stage in the research and experimentation process.

📂 Notebooks Summary
Notebook	Description

01_resnet_img_processing.ipynb	Extracted image embeddings using ResNet18 for each Fakeddit post.

02_roberta.ipynb	Generated text embeddings using BERT (later replaced by RoBERTa for improved context understanding).

03_resnet.ipynb	Experimented with additional ResNet architectures and fine-tuning image feature extraction.

04_DeepFusionNet_resNet_train.ipynb	Trained various fusion-based models (CNN-LSTM, MLP fusion) using pre-extracted embeddings. Compared performance metrics.

05_clip.ipynb	Used CLIP ViT-B/32 for joint image–text feature extraction and evaluated multimodal representations.

06_fusion_experiments.ipynb	Explored different fusion techniques (weighted averaging, concatenation, attention-based) with various weight combinations.

07_xgboost_author_features.ipynb	Added author and subreddit metadata as input features. Subreddit caused overfitting (accuracy=1.0), so final experiments used author features + other metadata + CLIP embeddings with XGBoost, resulting in 93.9% accuracy.

🧠 Key Insights
Initial models used BERT + ResNet18, giving strong baseline results.
CLIP-based embeddings provided superior joint understanding of visual and textual modalities.
Metadata experiments showed that:
Adding subreddit led to severe overfitting (accuracy, precision, F1 = 1.0).
Adding author improved model generalization.
XGBoost performed best as a classifier on top of CLIP embeddings.

📊 Results Summary
Model / Configuration	Description	Accuracy
BERT + ResNet18 Fusion	Early fusion of text & image embeddings	0.89
DeepFusionNet (ResNet + Text Encoder)	Custom MLP fusion	0.91
CLIP (ViT-B/32)	Vision-language embeddings	0.939
CLIP + Author + XGBoost	Final configuration	Best: 93.9%

⚙️ Technologies Used
Python, Google Colab
PyTorch, Transformers (Hugging Face)
OpenAI CLIP
ResNet, BERT, RoBERTa
XGBoost
Pandas, NumPy, Matplotlib, tqdm

🚀 How to Run
Clone this repository:
git clone https://github.com/VishalDhariwal/Fakeddit-Multimodal-FakeNews.git
cd fakeddit_models
Install dependencies:
pip install -r requirements.txt
Open the notebooks in Google Colab or Jupyter Notebook and run them sequentially.

🧩 Future Work
Experiment with cross-attention fusion for deeper image–text alignment
Try fine-tuned CLIP models on Fakeddit
Try VIT-L14 for training
Add explainability visualizations (e.g., Grad-CAM for image saliency)
Deploy the best-performing model via Gradio or Streamlit
