import sys
import pymupdf

doc = pymupdf.open(sys.argv[1])
print("pages:", len(doc))
toc = doc.get_toc()
print("TOC entries:", len(toc))
for t in toc[:30]:
    print(t)
for pno in range(2, 7):
    text = doc[pno].get_text()
    print(f"---- page {pno + 1}: {len(text)} chars")
    print(text[:500])