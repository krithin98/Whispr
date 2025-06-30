import pdfplumber

input_pdf = 'Trading System Documentation Copy.pdf'
output_md = 'Trading System Documentation Copy.md'

with pdfplumber.open(input_pdf) as pdf:
    all_text = ''
    for page in pdf.pages:
        all_text += page.extract_text() + '\n\n'

with open(output_md, 'w', encoding='utf-8') as f:
    f.write(all_text)

print(f'Converted {input_pdf} to {output_md}') 