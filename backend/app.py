from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re

app = Flask(__name__)
CORS(app)

# ✅ Segmenter
def segment_pdf(doc, segment_size=10):
    total_pages = len(doc)
    for i in range(0, total_pages, segment_size):
        print(f"📄 Segment: pages {i} to {min(i + segment_size, total_pages) - 1}")
        yield [doc.load_page(j) for j in range(i, min(i + segment_size, total_pages))]

# ✅ Better OCR
def ocr_page_to_text(page):
    pix = page.get_pixmap(dpi=400)  # High-res
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data)).convert("L")  # Grayscale
    return pytesseract.image_to_string(img, config='--psm 6')

# ✅ Smart fallback MCQ extractor for poor OCR
def fallback_extract_mcqs(text):
    mcqs = []
    blocks = re.split(r'\n\s*(?=\d{1,3}[\).])', text)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue

        # Try to separate question and options
        parts = re.split(r'\s*(a[\).])\s*', block, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) < 3:
            continue

        question = parts[0].strip()
        options_block = parts[1] + parts[2]

        options = re.findall(r'([a-dA-D])[\).]\s*(.*?)\s*(?=([a-dA-D][\).])|$)', options_block, re.DOTALL)
        option_list = [opt[1].strip().replace('\n', ' ') for opt in options]

        if len(option_list) >= 2:
            mcqs.append({
                "number": len(mcqs) + 1,
                "question": question.replace('\n', ' '),
                "options": option_list[:4]
            })

    print(f"✅ [Fallback] Extracted {len(mcqs)} MCQs")
    return mcqs

# ✅ Main extractor (from structured PDFs or clean OCR)
def extract_mcqs_from_text(text):
    lines = text.splitlines()
    mcqs = []
    current_q = ""
    current_opts = {}
    current_number = None
    question_started = False

    for line in lines:
        line = line.strip()

        if not line:
            continue

        match_q = re.match(r'^(\d{1,3})\.\s*(.*)', line)
        match_opt = re.match(r'^(a|b|c|d)[\).]\s*(.*)', line.lower())

        if match_q:
            if current_q and len(current_opts) == 4:
                mcqs.append({
                    "number": int(current_number),
                    "question": current_q.strip(),
                    "options": [
                        current_opts.get('a', ''),
                        current_opts.get('b', ''),
                        current_opts.get('c', ''),
                        current_opts.get('d', '')
                    ]
                })
            current_number = match_q.group(1)
            current_q = match_q.group(2)
            current_opts = {}
            question_started = True

        elif match_opt:
            key = match_opt.group(1)
            val = match_opt.group(2)
            current_opts[key] = val

        else:
            if current_opts and len(current_opts) < 4:
                last_key = list(current_opts.keys())[-1]
                current_opts[last_key] += ' ' + line
            elif question_started:
                current_q += ' ' + line

    # Final MCQ
    if current_q and len(current_opts) == 4 and current_number:
        mcqs.append({
            "number": int(current_number),
            "question": current_q.strip(),
            "options": [
                current_opts.get('a', ''),
                current_opts.get('b', ''),
                current_opts.get('c', ''),
                current_opts.get('d', '')
            ]
        })

    print(f"✅ [Structured] Extracted {len(mcqs)} MCQs")
    return mcqs

# ✅ Upload endpoint
@app.route('/upload', methods=['POST'])
def upload_pdf():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file uploaded'}), 400

        pdf = fitz.open(stream=file.read(), filetype="pdf")
        all_mcqs = []
        fallback_used = False

        for segment in segment_pdf(pdf, segment_size=10):
            segment_text = ""
            for page in segment:
                try:
                    text = page.get_text().strip()
                    if not text or len(text) < 20:
                        print("🔍 No text — using OCR")
                        text = ocr_page_to_text(page)
                except Exception as e:
                    print(f"❌ Error during text extraction: {e}")
                    text = ocr_page_to_text(page)

                segment_text += "\n" + text

            mcqs = extract_mcqs_from_text(segment_text)

            if len(mcqs) < 5:
                print("⚠️ Few MCQs found — falling back to OCR-based logic")
                mcqs = fallback_extract_mcqs(segment_text)
                fallback_used = True

            all_mcqs.extend(mcqs)

        print(f"🎉 Done! Total MCQs extracted: {len(all_mcqs)}")
        all_mcqs = sorted(all_mcqs, key=lambda x: x['number'])

        return jsonify({'mcqs': all_mcqs, 'fallback_used': fallback_used})

    except Exception as e:
        print("🛑 Internal Server Error:", e)
        return jsonify({'error': 'Internal server error'}), 500

# ✅ Start server
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
