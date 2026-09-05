import pptx
from pptx.util import Pt
from pptx.dml.color import RGBColor

file_path = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Presentations/experimental_literature_review.pptx"
prs = pptx.Presentation(file_path)

WHITE = RGBColor(255, 255, 255)
LIGHT_GRAY = RGBColor(220, 220, 220)

# Slide 2:
s2 = prs.slides[1]
p18 = s2.shapes[18].text_frame.paragraphs[0]
for r in p18.runs: r.font.color.rgb = WHITE
p19 = s2.shapes[19].text_frame.paragraphs[0]
for r in p19.runs: r.font.color.rgb = LIGHT_GRAY

# Slide 3:
s3 = prs.slides[2]
p18 = s3.shapes[18].text_frame.paragraphs[0]
for r in p18.runs: r.font.color.rgb = LIGHT_GRAY

# Slide 4:
s4 = prs.slides[3]
p18 = s4.shapes[18].text_frame.paragraphs[0]
for r in p18.runs: r.font.color.rgb = LIGHT_GRAY

# Slide 5:
s5 = prs.slides[4]
p15 = s5.shapes[15].text_frame.paragraphs[0]
for r in p15.runs: r.font.color.rgb = LIGHT_GRAY

# Slide 6:
s6 = prs.slides[5]
p15 = s6.shapes[15].text_frame.paragraphs[0]
for r in p15.runs: r.font.color.rgb = WHITE
p16 = s6.shapes[16].text_frame.paragraphs[0]
for r in p16.runs: r.font.color.rgb = LIGHT_GRAY

prs.save(file_path)
print("Updated results text color to white!")
