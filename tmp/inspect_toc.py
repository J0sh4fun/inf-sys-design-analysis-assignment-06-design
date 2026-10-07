from docx import Document

p = r"D:\My workspace\Project\HTTT-assignment06\output\docx\A6_V1_03_NguyenTienDat017.docx"
d = Document(p)
for i, paragraph in enumerate(d.paragraphs):
    if paragraph.style.name.startswith("TOC"):
        sizes = [run.font.size.pt if run.font.size else None for run in paragraph.runs]
        print(i, paragraph.style.name, sizes, paragraph.text[:60])
