import streamlit as st
import re
import base64
import math
import streamlit.components.v1 as components


st.title("STËLZ SVG Generator")

uploaded_svg = st.file_uploader("Upload your SVG file", type=["svg"])
uploaded_font_text = st.file_uploader("Upload font for text (OTF/TTF)", type=["otf", "ttf"], key="font_logo")

user_text = st.text_input("Logo/Main text (replaces main path):", "Matcha")
name_text = st.text_input("Name (curved):", "Katja")

text_color = st.color_picker("Logo/main text color:", "#F5457F")
main_color = st.color_picker("Main color (replaces #F3E500):", "#A8D48C")
secondary_color = st.color_picker("Secondary color (replaces #D79C1E):", "#88A585")

def split_user_text_to_lines(txt: str):
    """Limit to max 2 words. If >2, keep first two and warn."""
    words = re.findall(r"\S+", txt.strip())
    if len(words) == 0:
        return []
    if len(words) > 2:
        st.warning("‘Logo/Main text’ supports max 2 words. Using the first two.")
        words = words[:2]
    return words

if uploaded_svg and uploaded_font_text:
    svg_text = uploaded_svg.read().decode("utf-8")

     # Ensure xlink namespace is present in the SVG tag
    if 'xmlns:xlink' not in svg_text:
        svg_text = re.sub(r'(<svg[^>]*?)((?:\s|>))', r'\1 xmlns:xlink="http://www.w3.org/1999/xlink"\2', svg_text, count=1)

    font_text_bytes = uploaded_font_text.read()
    font_text_base64 = base64.b64encode(font_text_bytes).decode("utf-8")

    # Remove the <path ... fill="#FF006F" ...> element (the logo graphic)
    svg_text = re.sub(r'<path[^>]*fill=["\']#FF006F["\'][^>]*/?>', '', svg_text, flags=re.IGNORECASE)

    # Embed both fonts in the SVG with a style tag
    font_face = f"""
    <style type="text/css">
    @font-face {{
      font-family: 'CustomTextFont';
      src: url(data:font/opentype;base64,{font_text_base64}) format('opentype');
    }}
    .custom-logo-text {{
      font-family: 'CustomTextFont';
      fill: {text_color};
      font-size: 150px;
      text-anchor: middle;
      dominant-baseline: middle;
    }}
    .custom-name-text {{
      font-family: 'CustomTextFont';
      fill: #000000;
      font-size: 70px;
      text-anchor: middle;
      dominant-baseline: middle;
      letter-spacing: 1.5px;
    }}
    </style>
    """

    # Insert the font-face after the opening <svg ...>
    svg_text = re.sub(r'(<svg[^>]*>)', r'\1' + font_face, svg_text, count=1)

    # --- NEW: handle 1- or 2-word user_text with size/lines ---
    lines = split_user_text_to_lines(user_text)
    if len(lines) == 1:
        # One word: single line at 80px
        logo_text = f'<text x="1130" y="1300" class="custom-logo-text" transform="rotate(-3.78 257 267)" font-size="150px">{lines[0]}</text>'
    elif len(lines) == 2:
        # Two words: stacked lines at 70px
        # Use tspans with dy to stack; first line nudged up, second line below
        line1, line2 = lines
        logo_text = f'''
        <text x="1130" y="1300" class="custom-logo-text" transform="rotate(-3.78 257 267)" font-size="120px">
          <tspan y="1300">{line1}</tspan>
          <tspan x="1100" y="1400">{line2}</tspan>
        </text>
        '''
    else:
        # No words entered -> empty logo text
        logo_text = ''

    # Arc path for name (you can adjust the arc's position/radius as needed)
    arc_path = '''
    <defs>
      <path id="arcPath" d="M880,425 A320,320 0 0,1 1140,100" fill="none"/>
    </defs>
    '''

    # Name along arc, rotated by 32.22°
    name_text_svg = f'''
    {arc_path}
    <g transform="rotate(4.22 880 425)">
      <text class="custom-name-text">
        <textPath xlink:href="#arcPath" startOffset="50%">
          {name_text}
        </textPath>
      </text>
    </g>
    '''

    # Insert both texts before </svg>
    svg_text = re.sub(r'(</svg>)', logo_text + name_text_svg + r'\1', svg_text, count=1)

    # Update colors
    svg_text = re.sub(r'#A8D48C', main_color, svg_text, flags=re.IGNORECASE)
    svg_text = re.sub(r'#88A585', secondary_color, svg_text, flags=re.IGNORECASE)

    st.markdown("### Preview of updated SVG")
    svg_b64 = base64.b64encode(svg_text.encode("utf-8")).decode("utf-8")
    st.markdown(f'<img src="data:image/svg+xml;base64,{svg_b64}" style="max-width:100%;">',
            unsafe_allow_html=True)

    st.download_button(
        label="Download updated SVG",
        data=svg_text,
        file_name="custom_logo_and_curved_name.svg",
        mime="image/svg+xml"
    )
else:
    st.info("Upload SVG and a font file to begin.")
