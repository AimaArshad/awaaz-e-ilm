import pymupdf

body = "This is sample body text for the chapter. " * 40
chapters = ["Chapter 1: Introduction", "Chapter 2: Methods", "Chapter 3: Results"]

def build(path, with_toc):
    doc = pymupdf.open()
    toc = []
    for i, title in enumerate(chapters):
        for p in range(2):
            page = doc.new_page()
            if p == 0:
                page.insert_text((72, 100), title, fontsize=24)
                toc.append([1, title, len(doc)])
            page.insert_textbox(pymupdf.Rect(72, 140, 520, 760), body, fontsize=11)
    if with_toc:
        doc.set_toc(toc)
    doc.save(path)
    doc.close()

build("book_no_toc.pdf", with_toc=False)
build("book_with_toc.pdf", with_toc=True)
print("created")