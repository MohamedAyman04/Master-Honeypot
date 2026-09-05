import pptx
from pptx.util import Pt
from pptx.dml.color import RGBColor
from copy import deepcopy

src_path = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Presentations/experimental_literature_review_backup.pptx"
dst_path = "/run/media/mohamed-ayman/External HD/Neutral_Files/GUC/Master's/Presentations/experimental_literature_review.pptx"

prs = pptx.Presentation(src_path)

slide4 = prs.slides[3]
slide5 = prs.slides[4]
slide6 = prs.slides[5]

# Elements to clone
s10_elem = deepcopy(slide4.shapes[10]._element)
s11_elem = deepcopy(slide4.shapes[11]._element)
s12_elem = deepcopy(slide4.shapes[12]._element)

# Slide 5: Add 3rd component
slide5.shapes._spTree.append(deepcopy(s10_elem))
slide5.shapes._spTree.append(deepcopy(s11_elem))
slide5.shapes._spTree.append(deepcopy(s12_elem))

title_shape_5 = slide5.shapes[-2]
desc_shape_5 = slide5.shapes[-1]

title_shape_5.text_frame.clear()
p_t5 = title_shape_5.text_frame.paragraphs[0]
r_t5 = p_t5.add_run()
r_t5.text = "Control loop runtime"
r_t5.font.name = "Calibri"
r_t5.font.size = Pt(12.5)
r_t5.font.bold = True
r_t5.font.color.rgb = RGBColor(0, 0, 0)

desc_shape_5.text_frame.clear()
p_d5 = desc_shape_5.text_frame.paragraphs[0]
r_d5 = p_d5.add_run()
r_d5.text = "MicroPython cyclic execution loop — executes deterministic sensor polling and PWM output calculations"
r_d5.font.name = "Calibri"
r_d5.font.size = Pt(11)
r_d5.font.bold = False
r_d5.font.color.rgb = RGBColor(0x3A, 0x3A, 0x3A)

# Slide 6: Add 3rd component
slide6.shapes._spTree.append(deepcopy(s10_elem))
slide6.shapes._spTree.append(deepcopy(s11_elem))
slide6.shapes._spTree.append(deepcopy(s12_elem))

title_shape_6 = slide6.shapes[-2]
desc_shape_6 = slide6.shapes[-1]

title_shape_6.text_frame.clear()
p_t6 = title_shape_6.text_frame.paragraphs[0]
r_t6 = p_t6.add_run()
r_t6.text = "Primary threat vectors"
r_t6.font.name = "Calibri"
r_t6.font.size = Pt(12.5)
r_t6.font.bold = True
r_t6.font.color.rgb = RGBColor(0, 0, 0)

desc_shape_6.text_frame.clear()
p_d6 = desc_shape_6.text_frame.paragraphs[0]
r_d6 = p_d6.add_run()
r_d6.text = "Unsecured external remote access connections, perimeter bridging, and unmonitored vendor maintenance channels"
r_d6.font.name = "Calibri"
r_d6.font.size = Pt(11)
r_d6.font.bold = False
r_d6.font.color.rgb = RGBColor(0x3A, 0x3A, 0x3A)

prs.save(dst_path)
print("Successfully fixed typography and alignment!")
