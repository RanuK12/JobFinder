import os
import logging
from pdfminer.high_level import extract_text
from docx import Document
import re
from typing import Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('static/logs/cv_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_cv(filepath: str) -> Optional[str]:
    """
    Extrae el texto de un archivo CV (PDF o DOCX).
    
    Args:
        filepath (str): Ruta al archivo del CV
        
    Returns:
        Optional[str]: Texto extraído del CV o None si hay error
        
    Raises:
        ValueError: Si el archivo no existe o no es un formato válido
    """
    logger.info(f"Iniciando parse_cv con archivo: {filepath}")
    
    if not filepath:
        logger.error("No se proporcionó un archivo")
        return None
        
    if not os.path.exists(filepath):
        logger.error(f"El archivo no existe: {filepath}")
        return None
        
    file_ext = os.path.splitext(filepath)[1].lower()
    logger.info(f"Procesando archivo: {filepath} con extensión: {file_ext}")
    
    try:
        if file_ext == '.pdf':
            logger.info("Extrayendo texto de PDF...")
            try:
                text = extract_text(filepath)
                logger.info(f"Texto extraído del PDF (primeros 100 caracteres): {text[:100] if text else 'None'}")
                if not text:
                    logger.error("No se pudo extraer texto del PDF")
                    return None
            except Exception as e:
                logger.error(f"Error extrayendo texto del PDF: {str(e)}")
                return None
                
        elif file_ext == '.docx':
            logger.info("Extrayendo texto de DOCX...")
            try:
                doc = Document(filepath)
                paragraphs = [paragraph.text for paragraph in doc.paragraphs]
                logger.info(f"Número de párrafos encontrados: {len(paragraphs)}")
                text = '\n'.join(paragraphs)
                logger.info(f"Texto extraído del DOCX (primeros 100 caracteres): {text[:100] if text else 'None'}")
                if not text:
                    logger.error("No se pudo extraer texto del DOCX")
                    return None
            except Exception as e:
                logger.error(f"Error extrayendo texto del DOCX: {str(e)}")
                return None
        else:
            logger.error(f"Formato de archivo no soportado: {file_ext}")
            return None
            
        # Asegurar que text sea una cadena
        if isinstance(text, list):
            logger.info("Convirtiendo lista a texto")
            text = ' '.join(text)
        elif not isinstance(text, str):
            logger.info(f"Convirtiendo {type(text)} a texto")
            text = str(text)
            
        # Limpiar y normalizar el texto
        text = re.sub(r'\s+', ' ', text)  # Reemplazar múltiples espacios con uno solo
        text = text.strip()
        
        if not text:
            logger.error("El archivo está vacío o no contiene texto legible")
            return None
            
        logger.info(f"Texto extraído exitosamente del archivo {filepath}")
        logger.info(f"Longitud del texto: {len(text)} caracteres")
        return text
        
    except Exception as e:
        logger.error(f"Error procesando archivo {filepath}: {str(e)}")
        return None