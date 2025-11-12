from sentence_transformers import SentenceTransformer
print("⏳ Descargando modelo 'all-MiniLM-L6-v2' de SentenceTransformers...")
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save('app/models/bert')
print("✅ Modelo guardado localmente en app/models/bert")
