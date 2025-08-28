import streamlit as st
import re
import base64
import math
import json
import streamlit.components.v1 as components

st.title("STËLZ SVG Generator")

# -----------------------------
# Session defaults
# -----------------------------
st.session_state.setdefault("text_color", "#F5457F")
st.session_state.setdefault("main_color", "#A8D48C")
st.session_state.setdefault("secondary_color", "#88A585")

# -----------------------------
# API key + flavor + AI button
# -----------------------------
openai_api_key = st.text_input("OpenAI API key", type="password", placeholder="sk-...")
flavor_input = st.text_input("Flavor (also shown as main logo text)", value="Matcha")

SYSTEM_PROMPT = """Jij bent een slimme assistent die altijd een JSON-object als input krijgt in deze vorm:

json
{
  "name": "Michael",
  "flavor": "Appel Citroen",
}
Jouw taak:

Analyseer de waarde van het veld "flavor" (bijvoorbeeld: "Appel Citroen").

Bedenk op basis van de smaak drie bijpassende kleuren in hexwaarden:

"mainColor" (de dominante kleur)

"secondaryColor" (een goed passende tweede kleur)

"textColor" (een passende kleur voor tekst op de mainColor achtergrond)

Lever als antwoord altijd een nieuw JSON-object, met exact dezelfde velden als de input én de drie extra kleurvelden, bijvoorbeeld:
json
{
  "name": "Michael",
  "flavor": "Appel Citroen",
  "mainColor": "#FFFD4A",
  "secondaryColor": "#34EF29",
  "textColor": "#FF0000"
}
Geef geen enkele uitleg of extra tekst, alleen het JSON-object als output. Geef het JSON-object als één enkele regel, zonder extra spaties, enters, of uitleg. Dus bijvoorbeeld: {"name":"Michael","flavor":"Appel Citroen","contactId":"444525470","mainColor":"#FFFD4A","secondaryColor":"#34EF29","textColor":"#FF0000"}"""

def _parse_one_line_json(s: str) -> dict:
    m = re.search(r"\{.*\}", s, flags=re.S)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return json.loads(m.group(0))

def _is_hex_color(val: str) -> bool:
    return isinstance(val, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}", val) is not None

def _normalize_hex(val: str) -> str:
    return val if val.startswith("#") else f"#{val}"

# IMPORTANT: Handle the button BEFORE creating the color pickers.
if st.button("Suggest colors from flavor"):
    if not openai_api_key:
        st.error("Please enter your OpenAI API key.")
    else:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)

            user_payload = {
                "name": "User",
                "flavor": flavor_input or "Unknown"
            }

            resp = client.chat.completions.create(
                model="gpt-5",
                temperature=1,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
                ]
            )

            raw = resp.choices[0].message.content.strip()
            data = _parse_one_line_json(raw)

            mc = _normalize_hex(data.get("mainColor", st.session_state.main_color))
            sc = _normalize_hex(data.get("secondaryColor", st.session_state.secondary_color))
            tc = _normalize_hex(data.get("textColor", st.session_state.text_color))

            if not all(map(_is_hex_color, [mc, sc, tc])):
                raise ValueError("Model returned invalid hex colors.")

            # Update BEFORE widgets are created
            st.session_state.main_color = mc
            st.session_state.secondary_color = sc
            st.session_state.text_color = tc

            # Rerun so the widgets below pick up new defaults
            st.success(f"Applied AI colors • main: {mc} • secondary: {sc} • text: {tc}")
            st.rerun()
        except Exception as e:
            st.error(f"AI color suggestion failed: {e}")

# -----------------------------
# File & text inputs
# -----------------------------
uploaded_svg = st.file_uploader("Upload your SVG file", type=["svg"])
uploaded_font_text = st.file_uploader("Upload font for text (OTF/TTF)", type=["otf", "ttf"], key="font_logo")
name_text = st.text_input("Name (curved):", "Katja")

# -----------------------------
# Color pickers (now safe)
# -----------------------------
text_color = st.color_picker("Logo/main text color:", key="text_color")
main_color = st.color_picker("Main color (replaces #A8D48C):", key="main_color")
secondary_color = st.color_picker("Secondary color (replaces #88A585):", key="secondary_color")

# -----------------------------
# Helpers
# -----------------------------
def split_user_text_to_lines(txt: str):
    """Limit to max 2 words. If >2, keep first two and warn."""
    words = re.findall(r"\S+", txt.strip())
    if len(words) == 0:
        return []
    if len(words) > 2:
        st.warning("‘Flavor’ supports max 2 words. Using the first two.")
        words = words[:2]
    return words

# -----------------------------
# SVG processing
# -----------------------------
if uploaded_svg and uploaded_font_text:
    svg_text = uploaded_svg.read().decode("utf-8")

    # Ensure xlink namespace is present in the SVG tag
    if 'xmlns:xlink' not in svg_text:
        svg_text = re.sub(r'(<svg[^>]*?)((?:\s|>))', r'\1 xmlns:xlink="http://www.w3.org/1999/xlink"\2', svg_text, count=1)

    font_text_bytes = uploaded_font_text.read()
    font_text_base64 = base64.b64encode(font_text_bytes).decode("utf-8")

    # Remove legacy pink path if present
    svg_text = re.sub(r'<path[^>]*fill=["\']#FF006F["\'][^>]*/?>', '', svg_text, flags=re.IGNORECASE)

    # Embed font and classes using session colors
    font_face = f"""
    <style type="text/css">
    @font-face {{
      font-family: 'CustomTextFont';
      src: url(data:font/opentype;base64,{font_text_base64}) format('opentype');
    }}
    .custom-logo-text {{
      font-family: 'CustomTextFont';
      fill: {st.session_state.text_color};
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

    # Handle 1- or 2-word main logo text (from flavor_input)
    lines = split_user_text_to_lines(flavor_input)
    if len(lines) == 1:
        logo_text = f'<text x="1130" y="1300" class="custom-logo-text" transform="rotate(-3.78 257 267)" font-size="150px">{lines[0]}</text>'
    elif len(lines) == 2:
        line1, line2 = lines
        logo_text = f'''
        <text x="1130" y="1300" class="custom-logo-text" transform="rotate(-3.78 257 267)" font-size="120px">
          <tspan y="1300">{line1}</tspan>
          <tspan x="1100" y="1400">{line2}</tspan>
        </text>
        '''
    else:
        logo_text = ''

    # Arc path for name
    arc_path = '''
    <defs>
      <path id="arcPath" d="M880,425 A320,320 0 0,1 1140,100" fill="none"/>
    </defs>
    '''

    # Name along arc
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

    # Apply main/secondary replacements from session
    svg_text = re.sub(r'#A8D48C', st.session_state.main_color, svg_text, flags=re.IGNORECASE)
    svg_text = re.sub(r'#88A585', st.session_state.secondary_color, svg_text, flags=re.IGNORECASE)

    st.markdown("### Preview of updated SVG")
    svg_b64 = base64.b64encode(svg_text.encode("utf-8")).decode("utf-8")
    st.markdown(f'<img src="data:image/svg+xml;base64,{svg_b64}" style="max-width:100%;">',
                unsafe_allow_html=True)

    st.download_button(
        label="Download updated SVG",
        data=svg_text.encode("utf-8"),
        file_name="custom_logo_and_curved_name.svg",
        mime="image/svg+xml;charset=utf-8"
    )
else:
    st.info("Upload SVG and a font file to begin.")
