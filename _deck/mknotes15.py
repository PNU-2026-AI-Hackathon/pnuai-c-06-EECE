"""새로 끼운 슬라이드용 노트 슬라이드를 만들고 등록한다."""
import shutil
from pathlib import Path
from defusedxml import minidom

B = Path("base")
src, dst = "notesSlide13.xml", "notesSlide15.xml"
shutil.copy(B / "ppt/notesSlides" / src, B / "ppt/notesSlides" / dst)
shutil.copy(B / f"ppt/notesSlides/_rels/{src}.rels", B / f"ppt/notesSlides/_rels/{dst}.rels")

rp = B / f"ppt/notesSlides/_rels/{dst}.rels"
d = minidom.parse(str(rp))
for r in d.getElementsByTagName("Relationship"):
    if "/slide" in r.getAttribute("Type"):
        r.setAttribute("Target", "../slides/slide15.xml")
rp.write_text(d.toxml(), encoding="utf-8")

sp = B / "ppt/slides/_rels/slide15.xml.rels"
d = minidom.parse(str(sp))
rel = d.createElement("Relationship")
rel.setAttribute("Id", "rIdNotes")
rel.setAttribute("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide")
rel.setAttribute("Target", f"../notesSlides/{dst}")
d.documentElement.appendChild(rel)
sp.write_text(d.toxml(), encoding="utf-8")

ct = B / "[Content_Types].xml"
d = minidom.parse(str(ct))
part = f"/ppt/notesSlides/{dst}"
if not any(o.getAttribute("PartName") == part for o in d.getElementsByTagName("Override")):
    o = d.createElement("Override")
    o.setAttribute("PartName", part)
    o.setAttribute("ContentType",
                   "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml")
    d.documentElement.appendChild(o)
    ct.write_text(d.toxml(), encoding="utf-8")
print("  notesSlide15 생성·등록")
