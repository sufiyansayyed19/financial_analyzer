import pdfplumber
import os
import time

pdf_path = "data/us/annual/nvidia/nvidia_2023_annual.pdf"

start_time = time.perf_counter()

with pdfplumber.open(pdf_path) as pdf:
    full_text = ""
    
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

end_time = time.perf_counter()

print("Total characters:", len(full_text))
print("Time taken (seconds):", round(end_time - start_time, 2))


# ---------- SAVE FILE ----------

# Create processed folder structure
output_path = pdf_path.replace("data", "processed").replace(".pdf", ".txt")

os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(full_text)

print("Saved to:", output_path)
