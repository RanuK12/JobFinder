from pdfminer.high_level import extract_text
from docx import Document

def parse_cv(filepath):
    try:
        if filepath.endswith('.pdf'):
            text = extract_text(filepath)
        elif filepath.endswith('.docx'):
            doc = Document(filepath)
            text = "\n".join([para.text for para in doc.paragraphs])
        else:
            raise ValueError("Formato no soportado")
        return text
    except Exception as e:
        print(f"Error parsing CV: {str(e)}")
        return ""