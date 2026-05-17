#!/usr/bin/env python3
"""Add FAQ sections (HTML + JSON-LD) to Oslo Bike Tours tour pages."""

import os
import re

BASE = "/Users/antonbaumann/Documents/oslo-tours"

# ─── FAQ content per tour ────────────────────────────────────────────────────

FAQS = {
    "oslo-city-highlights": [
        (
            "What landmarks does the Oslo City Highlights tour cover?",
            "The route takes in Oslo's greatest hits in a single loop: the Oslo Opera House and Bjørvika waterfront, Aker Brygge harbour, the emerging Fjord City district, St. Hanshaugen, Vigeland Sculpture Park with its 200 bronze and granite figures, the Royal Palace gardens and Karl Johans gate — Oslo's main boulevard.",
        ),
        (
            "Is the Oslo City Highlights tour suitable for children and families?",
            "Yes. The route runs entirely on flat, paved roads and dedicated cycle lanes through central Oslo. There are no significant climbs. Children who are comfortable cycling on roads are welcome, and the pace is kept relaxed throughout.",
        ),
        (
            "How does the Oslo City Highlights tour differ from the Bygdøy Peninsula tour?",
            "City Highlights focuses on the urban core — waterfront, sculpture park, palace and boulevard — and is the shorter of the two at 18 km. The Bygdøy tour heads west along the fjord to a quieter, more forested peninsula with museum culture and open water views. Many guests do both on the same trip.",
        ),
        (
            "Can I join the Oslo City Highlights tour on an e-bike?",
            "Yes. The City Highlights route is well suited to e-bikes — the terrain is flat and entirely on-road, and the lower speed is no obstacle on a route with this much to look at. E-bike rentals are available on request when you book.",
        ),
        (
            "What time of day does the Oslo City Highlights tour run?",
            "There are no fixed departure times. Tours run by appointment, so you choose the time that suits your schedule. Morning tours offer quieter roads and softer light on the waterfront. Evening tours in summer benefit from Oslo's long golden hours.",
        ),
    ],
    "bygdoy-peninsula": [
        (
            "Which museums are on the Bygdøy Peninsula route?",
            "The route passes the Norwegian Folk Museum, the Viking Ship Museum and the Fram Museum — home to the world's best-preserved polar exploration vessel. Your guide will bring the history and context alive as you ride. If you want to go inside any of the museums you can do so independently before or after the tour.",
        ),
        (
            "Do we go inside the museums on the Bygdøy Peninsula tour?",
            "No — the bike tour rides past the museum buildings with guided commentary rather than going inside. This keeps the momentum of the ride and lets your guide connect the sites as part of a wider story about Oslo and Norway. Museum entry is easy to arrange independently if you want to explore further.",
        ),
        (
            "How hilly is the Bygdøy Peninsula bike tour?",
            "There is one moderate climb as the route ascends onto the peninsula — it is short and manageable for most riders. The rest of the route is flat or gently rolling along the fjord shore and through the tree-lined peninsula roads. It is not classified as a challenging tour.",
        ),
        (
            "What is the best season for the Bygdøy Peninsula bike tour?",
            "The tour runs year-round, but late spring through early autumn is the best time for fjord views and comfortable cycling. The peninsula's chestnut trees are in full leaf from May onwards, the bathing beaches along Frognerkilen come alive in summer, and the water views on the return leg are particularly beautiful on clear days.",
        ),
        (
            "Is the Bygdøy Peninsula tour a good option for someone visiting Oslo for the first time?",
            "Yes, though it pairs especially well with the Oslo City Highlights tour if you have more than one day. City Highlights covers the urban landmarks — the Opera House, Vigeland Park, the Palace — while Bygdøy adds the fjord, the peninsula roads and Norway's maritime and Viking history. Together they give a thorough picture of Oslo.",
        ),
    ],
    "nordmarka-forest": [
        (
            "What exactly is the Ring 4 route in Nordmarka?",
            "Ring 4 refers to the fourth of the concentric trail rings mapped out from Oslo into the Nordmarka forest. It is a classic loop that local cyclists have been riding for generations — a 45 km circuit of pine and birch forest on gravel roads, passing Kikutstua cabin and looping back through the Maridalen valley. It is the most popular intermediate forest route in Oslo.",
        ),
        (
            "What type of bike do I need for the Nordmarka Forest Ring 4 tour?",
            "A gravel bike is the right tool for Ring 4. The roads are gravel throughout — smooth enough to roll at speed on most sections, but a road bike with narrow tyres would be uncomfortable and inefficient. Gravel bike rentals are available if you do not have your own. E-bikes are not recommended on this route due to distance and terrain variability.",
        ),
        (
            "How much elevation gain is on the Nordmarka Ring 4 tour?",
            "Approximately 800 metres of total elevation gain spread across the 45 km loop. The climbs are sustained but never brutal — long enough to feel like proper effort, with equally long descents that make them worthwhile. Recreational riders who cycle regularly will find it manageable.",
        ),
        (
            "What is Kikutstua and do we stop there?",
            "Kikutstua is a traditional Norwegian mountain cabin about halfway around the Ring 4 loop, run by the Norwegian Trekking Association. It serves waffles and coffee and is a beloved institution for Oslo cyclists. Yes — we stop there for a proper break mid-ride, which is as much a part of the Ring 4 experience as the forest itself.",
        ),
        (
            "Is the Nordmarka Forest Ring 4 tour suitable for someone who cycles occasionally but not regularly?",
            "It is on the edge of what we would recommend for occasional cyclists. At 45 km on gravel with 800 m of climbing, it asks for a baseline of fitness. If you cycle a few times a month and are comfortable on a bike for 3–4 hours, you will manage it. If you are looking for something less demanding, the Oslo City Highlights or Bygdøy Peninsula tours are better starting points.",
        ),
    ],
    "epic-marka-endurance": [
        (
            "How physically demanding is the Epic Marka Endurance tour?",
            "It is our most demanding tour by a significant margin — 85 km of gravel with approximately 1,500 metres of elevation gain over six hours. Good cycling fitness is genuinely required. This is a full-day ride into remote terrain, not a leisure outing. If you are unsure whether it suits your fitness level, email us and we can talk it through.",
        ),
        (
            "What food and drink is provided on the Epic Marka Endurance tour?",
            "A lunch stop at a remote trailside cabin is included in the route — eaten outside, whatever the weather. We recommend bringing additional snacks and at least 1.5 litres of water from the start. There are no shops or cafés in the deep forest sections of the route.",
        ),
        (
            "What should I bring for the Epic Marka Endurance full-day ride?",
            "Waterproofs are essential — Nordmarka weather can change quickly and we ride regardless of rain. Bring extra layers, a buff or hat, cycling gloves, and sunscreen for clear days. Padded shorts are strongly recommended for an 85 km gravel ride. Your guide will have a basic first aid kit and puncture repair supplies.",
        ),
        (
            "Is the Epic Marka Endurance tour available on an e-bike?",
            "No. The route goes deep into areas where charging is not possible and where the terrain — loose stone, rooted tracks, long gravel climbs — makes e-bike handling genuinely difficult. The Epic Marka tour is designed for riders on performance gravel bikes. E-bikes are available on other tours in our programme.",
        ),
        (
            "Can a group of mixed abilities do the Epic Marka Endurance tour together?",
            "Only if everyone in the group meets the fitness requirement. Unlike our easier tours where pace can be varied widely, the Epic Marka route involves sustained effort over six hours and remote terrain where a struggling rider affects the whole group significantly. If your group has mixed fitness levels, we recommend splitting across different tours.",
        ),
    ],
    "oslo-coffee-tour": [
        (
            "Which coffee shops does the Oslo Coffee Tour visit, and in what order?",
            "The tour visits four Oslo specialty coffee institutions: Tim Wendelboe in Grünerløkka (World Barista Champion 2004, and one of the world's most influential roasters), Supreme Roastworks at Vulkan by the Akerselva river, Fuglen in Frogner (mid-century interior, global cult following), and Java in Frogner (Oslo's original specialty coffee shop, open since 1997). The exact order follows a logical route through the city.",
        ),
        (
            "Is the coffee and food included in the Oslo Coffee Tour price?",
            "Yes. A coffee and a pastry at each of the four stops is included in the NOK 1,190 price. You are not expected to pay anything at the coffee shops themselves. If you want additional items beyond what is included, you are welcome to order and pay independently.",
        ),
        (
            "Do I need to be a coffee enthusiast to enjoy the Oslo Coffee Tour?",
            "Not at all. The tour is designed to be enjoyable for anyone curious about food culture, neighbourhoods and craft — not just dedicated coffee people. Your guide provides context about each roaster and what makes Oslo's coffee scene unusual without it becoming a lecture. Guests who arrive knowing little about specialty coffee often find it one of the most interesting parts of their Oslo trip.",
        ),
        (
            "What kind of bike do I need for the Oslo Coffee Tour?",
            "Any bike is suitable — the route is entirely on flat, paved urban roads. If you have your own road or hybrid bike, bring it. If not, e-bike and gravel bike rentals are available on request. The 22 km distance and relaxed pace also make it one of the few tours where a slower e-bike is just as enjoyable as a road bike.",
        ),
        (
            "Can the Oslo Coffee Tour be combined with another tour on the same day?",
            "Yes, easily. At 22 km and 3 hours, the Coffee Tour is the lightest in the programme. It pairs well with the Oslo City Highlights tour in the morning followed by Coffee in the afternoon, or vice versa. Some guests also combine it with the Architecture Tour, which covers similar neighbourhoods from a different angle.",
        ),
    ],
    "oslo-architecture-tour": [
        (
            "Which buildings does the Oslo Architecture Tour visit?",
            "The tour visits five key sites in Oslo's Nordic functionalist legacy: Havna Allé (Korsmo, 1930–32) — Oslo's first functionalist housing development, a serene cul-de-sac of flat-roofed concrete villas; Villa Stenersen (Korsmo, 1937–39) — an open-plan villa built for art collector Rolf Stenersen, now preserved by the National Museum; Planetveien 12 (Korsmo, 1955); Villa Dammann (1930–32); and Skådalen School (Sverre Fehn, 1977) — one of Norway's greatest architects working at his most considered.",
        ),
        (
            "What is Nordic functionalism and why does Oslo have so much of it?",
            "Nordic functionalism emerged in the late 1920s and 1930s as Scandinavian architects adopted the clean lines, flat roofs and open plans of European modernism and filtered them through a northern sensibility — less dogmatic, more liveable, deeply concerned with light and landscape. Oslo became an important centre for the movement partly through architects like Arne Korsmo, who studied and corresponded with the leading figures of European modernism and brought those ideas back to Norwegian domestic architecture.",
        ),
        (
            "Do I need an architecture background to enjoy the Oslo Architecture Tour?",
            "No. The tour is built around storytelling — who commissioned these buildings, what they were trying to say, what was radical about them at the time, and how they sit in their streets today. Guests with no architecture background consistently find it one of the most engaging tours in the programme. An interest in history, design or cities is all you need.",
        ),
        (
            "Can we go inside any of the buildings on the Oslo Architecture Tour?",
            "The buildings visited are private residences or protected structures, so interiors are not part of the tour. Your guide will take you as close as public access allows and bring the architecture alive through explanation, photographs and context. Villa Stenersen's interior can occasionally be visited through the National Museum's programme — worth checking if it is a particular interest.",
        ),
        (
            "How does the Oslo Architecture Tour compare to the Oslo City Highlights tour in terms of route and difficulty?",
            "They are similar in distance and effort — both are 30 km or under on paved roads with gentle terrain, suitable for all fitness levels. The difference is entirely in focus. City Highlights is a broad survey of Oslo's famous landmarks; the Architecture Tour is a slow, deliberate exploration of a specific chapter in design history. Some guests do City Highlights on day one to get oriented, then the Architecture Tour on day two.",
        ),
    ],
}

TOUR_FILES = [
    "oslo-city-highlights/index.html",
    "bygdoy-peninsula/index.html",
    "nordmarka-forest/index.html",
    "epic-marka-endurance/index.html",
    "oslo-coffee-tour/index.html",
    "oslo-architecture-tour/index.html",
]


def build_faq_html(faqs):
    items = []
    for q, a in faqs:
        items.append(
            f'        <details class="faq__item">\n'
            f'          <summary class="faq__question">{q}</summary>\n'
            f'          <p class="faq__answer">{a}</p>\n'
            f'        </details>'
        )
    items_str = "\n".join(items)
    return (
        '  <!-- ─── FAQ ──────────────────────────────────────────────────── -->\n'
        '  <section class="faq section">\n'
        '    <div class="container">\n'
        '      <div class="section-header">\n'
        '        <span class="tag">FAQ</span>\n'
        '        <h2 class="section-title">Common questions</h2>\n'
        '      </div>\n'
        '      <div class="faq__list">\n'
        f'{items_str}\n'
        '      </div>\n'
        '    </div>\n'
        '  </section>\n'
        '\n'
    )


def build_faqpage_jsonld(faqs):
    entities = []
    for q, a in faqs:
        # Escape quotes for JSON
        q_esc = q.replace('"', '\\"')
        a_esc = a.replace('"', '\\"')
        entities.append(
            '          {\n'
            '            "@type": "Question",\n'
            f'            "name": "{q_esc}",\n'
            f'            "acceptedAnswer": {{ "@type": "Answer", "text": "{a_esc}" }}\n'
            '          }'
        )
    entities_str = ',\n'.join(entities)
    return (
        '      ,{\n'
        '        "@type": "FAQPage",\n'
        '        "mainEntity": [\n'
        f'{entities_str}\n'
        '        ]\n'
        '      }\n'
    )


def process_file(rel_path):
    tour_key = rel_path.split("/")[0]
    full_path = os.path.join(BASE, rel_path)

    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()

    faqs = FAQS[tour_key]

    # ── 1. Insert FAQPage into JSON-LD @graph ────────────────────────────────
    # Pattern: the closing ] of @graph followed by closing } of outer object
    # Looks like:  \n    ]\n  }\n  </script>
    jsonld_close_pattern = r'(\n    \]\n  \})'
    faqpage_json = build_faqpage_jsonld(faqs)

    matches = list(re.finditer(jsonld_close_pattern, content))
    if not matches:
        print(f"  WARNING: could not find @graph closing pattern in {rel_path}")
    else:
        # Use the first (and should be only) match
        m = matches[0]
        insert_pos = m.start()
        content = content[:insert_pos] + "\n" + faqpage_json.rstrip("\n") + content[insert_pos:]

    # ── 2. Insert FAQ HTML before footer comment ─────────────────────────────
    footer_marker = "  <!-- ─── Footer"
    footer_pos = content.find(footer_marker)
    if footer_pos == -1:
        print(f"  WARNING: could not find Footer comment in {rel_path}")
    else:
        faq_html = build_faq_html(faqs)
        content = content[:footer_pos] + faq_html + content[footer_pos:]

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  Modified: {rel_path}")


def main():
    print("Adding FAQ sections to Oslo Bike Tours pages...\n")
    for rel_path in TOUR_FILES:
        process_file(rel_path)
    print("\nDone.")


if __name__ == "__main__":
    main()
