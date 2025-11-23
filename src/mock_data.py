"""
Mock data generator for Formarter.

Generates 100 paragraphs organized into sections with sub-items,
demonstrating proper federal court filing format.
"""

from .models import Document, Section, SubItem


def create_mock_document() -> Document:
    """
    Create a mock federal court complaint with 100 paragraphs.

    Structure:
    - I. PARTIES (paras 1-8)
    - II. JURISDICTION AND VENUE (paras 9-14)
    - III. FACTUAL ALLEGATIONS (paras 15-75)
        - a. Background (15-25)
        - b. The Contract (26-40)
        - c. Defendant's Breach (41-55)
        - d. Damages Suffered (56-75)
    - IV. CAUSES OF ACTION (paras 76-92)
        - a. First Cause of Action: Breach of Contract (76-82)
        - b. Second Cause of Action: Fraud (83-88)
        - c. Third Cause of Action: Negligent Misrepresentation (89-92)
    - V. PRAYER FOR RELIEF (paras 93-100)
    """
    doc = Document(title="Smith v. ABC Corporation - Complaint")

    # ===== I. PARTIES =====
    sec1 = doc.add_section("I", "PARTIES")

    doc.add_paragraph(
        "Plaintiff John Smith ('Plaintiff') is an individual residing in Jackson, "
        "Hinds County, Mississippi. Plaintiff has been a resident of the State of "
        "Mississippi for the past fifteen years.",
        "I"
    )
    doc.add_paragraph(
        "Plaintiff is a licensed contractor engaged in the business of commercial "
        "construction and renovation in the greater Jackson metropolitan area.",
        "I"
    )
    doc.add_paragraph(
        "Defendant ABC Corporation ('Defendant' or 'ABC') is a Delaware corporation "
        "with its principal place of business located at 100 Commerce Street, "
        "Biloxi, Harrison County, Mississippi 39530.",
        "I"
    )
    doc.add_paragraph(
        "Defendant is registered to do business in the State of Mississippi and "
        "regularly conducts business throughout the State, including in Hinds County.",
        "I"
    )
    doc.add_paragraph(
        "At all times relevant hereto, Defendant held itself out to the public as "
        "a supplier of commercial-grade construction equipment and materials.",
        "I"
    )
    doc.add_paragraph(
        "Defendant maintains a warehouse and distribution center in Jackson, "
        "Mississippi, from which it ships equipment throughout the southeastern "
        "United States.",
        "I"
    )
    doc.add_paragraph(
        "Upon information and belief, Defendant employs approximately 150 persons "
        "in the State of Mississippi and has annual revenues exceeding $50 million.",
        "I"
    )
    doc.add_paragraph(
        "Defendant's registered agent for service of process in Mississippi is "
        "Corporation Service Company, located at 306 East Pearl Street, Jackson, "
        "Mississippi 39201.",
        "I"
    )

    # ===== II. JURISDICTION AND VENUE =====
    sec2 = doc.add_section("II", "JURISDICTION AND VENUE")

    doc.add_paragraph(
        "This Court has subject matter jurisdiction over this action pursuant to "
        "28 U.S.C. Section 1332 because there is complete diversity of citizenship "
        "between the parties and the amount in controversy exceeds $75,000, "
        "exclusive of interest and costs.",
        "II"
    )
    doc.add_paragraph(
        "Plaintiff is a citizen of the State of Mississippi. Defendant is a "
        "citizen of the State of Delaware, its state of incorporation, and the "
        "State of Mississippi, where it maintains its principal place of business.",
        "II"
    )
    doc.add_paragraph(
        "For purposes of diversity jurisdiction, Defendant is deemed a citizen "
        "only of Delaware, as a corporation's citizenship is determined by its "
        "state of incorporation and principal place of business.",
        "II"
    )
    doc.add_paragraph(
        "The amount in controversy in this action exceeds $75,000, exclusive of "
        "interest and costs, as Plaintiff seeks damages in excess of $500,000.",
        "II"
    )
    doc.add_paragraph(
        "Venue is proper in this District pursuant to 28 U.S.C. Section 1391(b)(2) "
        "because a substantial part of the events or omissions giving rise to the "
        "claims occurred in this District.",
        "II"
    )
    doc.add_paragraph(
        "Alternatively, venue is proper pursuant to 28 U.S.C. Section 1391(b)(1) "
        "because Defendant resides in this District for venue purposes, maintaining "
        "its principal place of business here.",
        "II"
    )

    # ===== III. FACTUAL ALLEGATIONS =====
    sec3 = doc.add_section("III", "FACTUAL ALLEGATIONS")

    # Add sub-items to section III
    sec3.subitems = [
        SubItem(id="a", title="Background"),
        SubItem(id="b", title="The Contract"),
        SubItem(id="c", title="Defendant's Breach"),
        SubItem(id="d", title="Damages Suffered"),
    ]

    # a. Background (paras 15-25)
    background_texts = [
        "Plaintiff has been engaged in the commercial construction business for "
        "over twenty years and has successfully completed numerous large-scale "
        "construction projects throughout Mississippi.",
        "In 2023, Plaintiff was awarded a contract to construct a new office "
        "complex for XYZ Development, LLC in downtown Jackson, Mississippi "
        "(the 'XYZ Project').",
        "The XYZ Project was valued at approximately $15 million and required "
        "Plaintiff to complete construction within eighteen months of commencement.",
        "The XYZ Project required specialized heavy construction equipment, "
        "including excavators, cranes, and concrete pumping equipment.",
        "Plaintiff had previously purchased equipment from various suppliers "
        "but had not previously done business with Defendant.",
        "In early January 2024, Plaintiff began soliciting bids from equipment "
        "suppliers for the machinery needed to complete the XYZ Project.",
        "Defendant's sales representative, James Wilson, contacted Plaintiff on "
        "January 5, 2024, to discuss Plaintiff's equipment needs.",
        "Mr. Wilson represented that Defendant could supply all of the equipment "
        "Plaintiff needed at competitive prices with guaranteed delivery times.",
        "Mr. Wilson specifically represented that Defendant had a large inventory "
        "of equipment available for immediate shipment from its Jackson warehouse.",
        "Based on Mr. Wilson's representations, Plaintiff invited Defendant to "
        "submit a formal bid for the equipment needed for the XYZ Project.",
        "On January 10, 2024, Defendant submitted a written proposal offering to "
        "supply the requested equipment for a total price of $850,000.",
    ]
    for text in background_texts:
        doc.add_paragraph(text, "III", "a")

    # b. The Contract (paras 26-40)
    contract_texts = [
        "On January 15, 2024, Plaintiff and Defendant entered into a written "
        "Equipment Purchase Agreement (the 'Agreement') for the purchase of "
        "construction equipment valued at $850,000.",
        "A true and correct copy of the Agreement is attached hereto as Exhibit A "
        "and incorporated herein by reference.",
        "Pursuant to the Agreement, Defendant agreed to deliver the following "
        "equipment to the XYZ Project site: two Caterpillar 320 excavators, one "
        "Liebherr LTM 1100 mobile crane, and two Putzmeister concrete pumps.",
        "The Agreement specified that all equipment would be new, unused, and in "
        "full working condition upon delivery.",
        "The Agreement expressly warranted that all equipment would conform to "
        "manufacturer specifications and would be free from defects in materials "
        "and workmanship.",
        "The Agreement required Defendant to deliver all equipment within thirty "
        "(30) days of the contract date, no later than February 14, 2024.",
        "Time was expressly made of the essence in the Agreement due to the tight "
        "construction schedule for the XYZ Project.",
        "The Agreement required Plaintiff to pay a deposit of $250,000 upon "
        "execution, with the balance due upon delivery and acceptance of the "
        "equipment.",
        "On January 15, 2024, Plaintiff paid the required deposit of $250,000 to "
        "Defendant by wire transfer.",
        "Defendant acknowledged receipt of the deposit and confirmed in writing "
        "that the equipment would be delivered on or before February 14, 2024.",
        "The Agreement contained an express warranty that the equipment would be "
        "fit for its intended purpose of commercial construction.",
        "The Agreement also contained Defendant's representation that it had clear "
        "title to all equipment and the authority to sell the same.",
        "Plaintiff relied upon Defendant's warranties and representations in "
        "entering into the Agreement.",
        "The Agreement was negotiated at arm's length between sophisticated "
        "commercial parties.",
        "The Agreement represents the complete and final understanding between "
        "the parties concerning the subject matter thereof.",
    ]
    for text in contract_texts:
        doc.add_paragraph(text, "III", "b")

    # c. Defendant's Breach (paras 41-55)
    breach_texts = [
        "Despite the clear terms of the Agreement, Defendant failed to deliver "
        "any equipment by the February 14, 2024 deadline.",
        "On February 10, 2024, Mr. Wilson contacted Plaintiff and stated that "
        "delivery would be delayed by approximately two weeks due to 'supply "
        "chain issues.'",
        "Plaintiff objected to the delay and reminded Defendant that time was of "
        "the essence under the Agreement.",
        "Mr. Wilson assured Plaintiff that Defendant was working to expedite "
        "delivery and that the equipment would arrive no later than March 1, 2024.",
        "Relying on these assurances, Plaintiff agreed to a brief extension of "
        "the delivery deadline to March 1, 2024.",
        "On March 1, 2024, Defendant delivered only one of the two excavators "
        "and none of the other contracted equipment.",
        "The excavator that was delivered was not new as warranted but was a "
        "refurbished unit with visible signs of prior use and wear.",
        "Upon inspection, Plaintiff discovered that the delivered excavator had "
        "over 2,000 hours of prior operation logged on its meter.",
        "The delivered excavator also exhibited mechanical problems, including "
        "hydraulic leaks and a malfunctioning control system.",
        "Plaintiff immediately notified Defendant in writing of the defects and "
        "demanded delivery of the remaining equipment and a conforming excavator.",
        "Defendant acknowledged the problems but failed to provide a satisfactory "
        "resolution or timeline for delivery of the remaining equipment.",
        "Over the following weeks, Plaintiff made numerous written and verbal "
        "demands for Defendant to fulfill its obligations under the Agreement.",
        "Despite these demands, Defendant failed to deliver the remaining "
        "equipment or replace the defective excavator.",
        "On April 15, 2024, Defendant's representative informed Plaintiff that "
        "Defendant could not fulfill the order and offered only to return "
        "Plaintiff's deposit.",
        "Plaintiff rejected this offer as inadequate given the damages already "
        "suffered as a result of Defendant's breach.",
    ]
    for text in breach_texts:
        doc.add_paragraph(text, "III", "c")

    # d. Damages Suffered (paras 56-75)
    damages_texts = [
        "As a direct and proximate result of Defendant's breach, Plaintiff has "
        "suffered significant damages.",
        "Due to the lack of necessary equipment, Plaintiff was forced to delay "
        "commencement of major construction activities on the XYZ Project.",
        "The delay in construction caused Plaintiff to miss critical project "
        "milestones established in its contract with XYZ Development, LLC.",
        "As a result of missing these milestones, Plaintiff incurred liquidated "
        "damages under its contract with XYZ Development, LLC in the amount of "
        "$50,000.",
        "Plaintiff was also forced to rent replacement equipment from other "
        "suppliers at significantly higher prices than the Agreement price.",
        "The cost of renting replacement equipment totaled $175,000 over the "
        "period from March 2024 through July 2024.",
        "The rental equipment was not identical to the contracted equipment and "
        "was less efficient, resulting in increased labor costs of approximately "
        "$45,000.",
        "Plaintiff was required to pay expedited shipping fees of $25,000 to "
        "obtain the rental equipment on an emergency basis.",
        "The project delays caused by Defendant's breach resulted in lost "
        "productivity valued at approximately $80,000.",
        "Plaintiff was also forced to pay overtime wages to workers to make up "
        "for lost time, totaling $35,000.",
        "The delays and equipment problems damaged Plaintiff's reputation with "
        "XYZ Development, LLC, resulting in the loss of future business "
        "opportunities.",
        "Upon information and belief, XYZ Development, LLC has declined to "
        "consider Plaintiff for two additional projects valued at over $20 million.",
        "Plaintiff also incurred attorney's fees and costs in attempting to "
        "resolve the dispute with Defendant prior to filing this action.",
        "The defective excavator delivered by Defendant caused damage to the "
        "XYZ Project site when its hydraulic system failed, releasing hydraulic "
        "fluid onto the ground.",
        "Plaintiff incurred environmental remediation costs of $15,000 to clean "
        "up the hydraulic fluid spill.",
        "Plaintiff was also required to pay $10,000 in fines to environmental "
        "regulators as a result of the spill.",
        "The total direct damages suffered by Plaintiff as a result of Defendant's "
        "breach exceed $435,000.",
        "Plaintiff is also entitled to consequential damages for lost profits and "
        "business opportunities in an amount to be proven at trial.",
        "Plaintiff's consequential damages are estimated to exceed $500,000.",
        "In total, Plaintiff has suffered damages in excess of $935,000 as a "
        "direct and proximate result of Defendant's breach of the Agreement.",
    ]
    for text in damages_texts:
        doc.add_paragraph(text, "III", "d")

    # ===== IV. CAUSES OF ACTION =====
    sec4 = doc.add_section("IV", "CAUSES OF ACTION")

    sec4.subitems = [
        SubItem(id="a", title="First Cause of Action: Breach of Contract"),
        SubItem(id="b", title="Second Cause of Action: Fraud"),
        SubItem(id="c", title="Third Cause of Action: Negligent Misrepresentation"),
    ]

    # a. First Cause of Action: Breach of Contract (paras 76-82)
    breach_coa_texts = [
        "Plaintiff incorporates by reference all preceding paragraphs as if fully "
        "set forth herein.",
        "Plaintiff and Defendant entered into a valid and enforceable contract, "
        "the Agreement, for the purchase and sale of construction equipment.",
        "Plaintiff fully performed all of its obligations under the Agreement, "
        "including payment of the required deposit.",
        "Defendant breached the Agreement by failing to deliver the contracted "
        "equipment within the time specified.",
        "Defendant further breached the Agreement by delivering defective "
        "equipment that did not conform to the contractual specifications.",
        "As a direct and proximate result of Defendant's breach, Plaintiff has "
        "suffered damages in an amount to be proven at trial, but not less than "
        "$500,000.",
        "Plaintiff is entitled to recover damages, including consequential "
        "damages, as a result of Defendant's breach of contract.",
    ]
    for text in breach_coa_texts:
        doc.add_paragraph(text, "IV", "a")

    # b. Second Cause of Action: Fraud (paras 83-88)
    fraud_coa_texts = [
        "Plaintiff incorporates by reference all preceding paragraphs as if fully "
        "set forth herein.",
        "Defendant, through its agent Mr. Wilson, made false representations of "
        "material fact to Plaintiff, including representations that equipment was "
        "available for immediate delivery and that all equipment would be new.",
        "Defendant knew at the time these representations were made that they "
        "were false, or made them with reckless disregard for their truth.",
        "Defendant made these representations with the intent to induce Plaintiff "
        "to enter into the Agreement and pay the deposit.",
        "Plaintiff reasonably relied upon Defendant's representations in entering "
        "into the Agreement.",
        "As a direct and proximate result of Defendant's fraud, Plaintiff has "
        "suffered damages in an amount to be proven at trial, and Plaintiff is "
        "entitled to punitive damages.",
    ]
    for text in fraud_coa_texts:
        doc.add_paragraph(text, "IV", "b")

    # c. Third Cause of Action: Negligent Misrepresentation (paras 89-92)
    negligent_coa_texts = [
        "Plaintiff incorporates by reference all preceding paragraphs as if fully "
        "set forth herein.",
        "In the alternative to the fraud claim, Defendant negligently made false "
        "representations of material fact to Plaintiff regarding the availability "
        "and condition of the equipment.",
        "Defendant owed a duty of care to Plaintiff to provide accurate "
        "information regarding the equipment, and Defendant breached that duty.",
        "As a direct and proximate result of Defendant's negligent "
        "misrepresentations, Plaintiff has suffered damages in an amount to be "
        "proven at trial.",
    ]
    for text in negligent_coa_texts:
        doc.add_paragraph(text, "IV", "c")

    # ===== V. PRAYER FOR RELIEF =====
    sec5 = doc.add_section("V", "PRAYER FOR RELIEF")

    prayer_texts = [
        "WHEREFORE, Plaintiff respectfully requests that this Court enter judgment "
        "in favor of Plaintiff and against Defendant as follows:",
        "For compensatory damages in an amount to be proven at trial, but not "
        "less than $500,000;",
        "For consequential damages, including lost profits and lost business "
        "opportunities, in an amount to be proven at trial;",
        "For punitive damages in an amount sufficient to punish Defendant and "
        "deter similar conduct in the future;",
        "For pre-judgment and post-judgment interest at the maximum rate allowed "
        "by law;",
        "For attorney's fees and costs of this action pursuant to applicable law;",
        "For a return of the $250,000 deposit paid by Plaintiff to Defendant;",
        "For such other and further relief as the Court deems just and proper.",
    ]
    for text in prayer_texts:
        doc.add_paragraph(text, "V")

    return doc


def get_document_as_text(doc: Document) -> str:
    """
    Convert document to plain text format showing paragraph numbers.
    """
    lines = []

    for section in doc.sections:
        # Section header (centered)
        lines.append("")
        lines.append(f"{'':^20}{section.id}. {section.title}")
        lines.append("")

        if section.subitems:
            for subitem in section.subitems:
                if subitem.title:
                    lines.append(f"    {subitem.id}. {subitem.title}")
                    lines.append("")
                for para_id in subitem.paragraph_ids:
                    para = doc.paragraphs.get(para_id)
                    if para:
                        lines.append(f"{para.number}.  {para.text}")
                        lines.append("")
        else:
            for para_id in section.paragraph_ids:
                para = doc.paragraphs.get(para_id)
                if para:
                    lines.append(f"{para.number}.  {para.text}")
                    lines.append("")

    return "\n".join(lines)
