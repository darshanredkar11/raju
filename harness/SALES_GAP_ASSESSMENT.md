# Sales-led gap assessment — Sanjay Chemicals

**Scope:** Public-facing sales journey and candidate operating improvements. This is not an audit of internal sales performance, inventory, margins, CRM, or response SLAs; those records have not been inspected.

## What the public evidence says

Sources reviewed:
- Company home: https://sanjaychemindia.com/
- Product catalogue: https://sanjaychemindia.com/products.php
- Industries served: https://www.sanjaychemindia.com/industries.php
- EVA product sheet: https://www.sanjaychemindia.com/pdfs/polymers/ETHYLENE-VINYL-ACETATE.pdf
- ChemicalDekho seller/RFQ offering: https://chemicaldekho.com/seller/
- ChemStock marketplace: https://chemstock.co.in/
- Frappe CRM: https://frappe.io/crm
- Frappe/ERPNext selling workflow: https://docs.frappe.io/erpnext/selling

## Salesperson's view: where revenue can leak

### 1. The catalogue is broad; the buyer needs a reason to enquire

**Observed:** The public product page lists many chemicals and several product families. The site has a broad contact path, while at least one product PDF provides a direct quote email. The public catalogue does not, in the pages reviewed, present one consistent, structured RFQ workflow for every product family.

**Commercial hypothesis:** A buyer can struggle to specify the exact grade, quantity, packaging, delivery point, required documents and target date in the first enquiry. Missing information creates avoidable back-and-forth and slower quotation.

**First action:** Use one RFQ intake standard across Harvey-assisted enquiries. Capture product/grade, quantity and unit, packaging, delivery city, required date, application if relevant, specification/CAS when applicable, required TDS/SDS/COA, and contact/organization. Never make up unavailable fields.

### 2. Product-specific demand is more valuable than generic company outreach

**Observed:** The company publicly lists polymers (EVA, PET, PVC), bulk and drum solvents, chemicals/intermediates, and speciality chemicals. It lists multiple served sectors, including packaging, plastics, paints/coatings, printing inks, pharmaceuticals, agrochemicals and water treatment.

**Commercial hypothesis:** Different product families require different buyer lists, buying triggers, technical proof and sales copy. A generic "we supply chemicals" email will waste the product breadth.

**First action:** Segment campaigns by exact product family and verified use case. Test one narrow product × buyer segment × geography combination at a time. Use the official product sheet or TDS/SDS as the claim boundary.

### 3. Public product presence is not proof of stock or quote readiness

**Observed:** Product presence and a product sheet establish public marketing information, not current inventory, supplier allocation, price, lead time or commercial availability.

**Commercial risk:** A fast AI-generated answer can overpromise stock, grade, origin or delivery and damage trust.

**First action:** Separate public product knowledge from live commercial facts. Any quote or availability claim must be confirmed by an authorized human or a trusted live inventory/ERP source. Until that source is integrated and tested, Harvey must draft a clarification/quote request, not promise terms.

### 4. Follow-up discipline can create more wins than more automation

**Observed:** No internal response-time, quote-to-order or lost-reason data was available for this review.

**Commercial hypothesis:** Sales can lose deals when enquiries have no owner, no promised next step, technical questions remain unanswered, or quotations are not followed up at a useful time.

**First action:** Record one owner, one stage, one next action/date, and one blocker per active opportunity. Measure acknowledgement time, complete-RFQ rate, quote turnaround, follow-up completion, quote-to-order conversion and loss reason before buying/building a CRM.

### 5. Product documentation is a conversion asset

**Observed:** The public site hosts at least one detailed EVA product PDF with properties, applications and a quote contact. A current, product-specific document is more useful than generic AI claims.

**Commercial hypothesis:** A consistent document pack by SKU can shorten technical qualification and improve buyer confidence.

**First action:** Inventory existing catalogue, TDS, SDS, COA policy, packaging options and approved claims by SKU. Treat only current approved documents as authoritative; do not assume every SKU has all documents.

### 6. New lead channels exist, but should be tested, not blindly integrated

**Existing candidates found:**
- ChemicalDekho advertises a chemical seller dashboard and buyer requirements/RFQs: https://chemicaldekho.com/seller/
- ChemStock advertises chemical inventory listings and requirement-based sourcing: https://chemstock.co.in/

**Commercial hypothesis:** These may add intent-bearing leads beyond cold outbound. Their actual buyer quality, fees, category coverage, lead ownership and conversion for Sanjay Chemicals are unverified.

**First action:** Compare channel economics and terms, then run a small, manually measured pilot only with approval. Do not scrape, subscribe, or spend money automatically.

## Proven components versus build decisions

| Need | Proven first choice | Decision |
|---|---|---|
| Prospect discovery, profiling, personalization, email drafts, reply handling | Harvey native agents, signals, skills, native mail integrations and Outbox | Configure and test before adding anything |
| Product knowledge | Harvey trainer + existing product_knowledge skill + approved product docs | Build a small evidence/claim overlay, not a new agent |
| RFQ capture and pipeline tracking | Existing company CRM/ERP if one exists; otherwise evaluate Frappe CRM / ERPNext's connected quotation workflow | Do not introduce a second CRM before confirming the current source of truth |
| Product-specific inbound lead generation | Test existing chemical marketplace channels such as ChemicalDekho and ChemStock | Manual pilot first; measure qualified RFQs and cost per qualified opportunity |
| TDS/SDS/COA retrieval | Existing controlled document store first | Only add document search/RAG if file volume and tests justify it |
| Alerts | Harvey native dashboard/Outbox first | No notification service until a concrete missed-alert use case is demonstrated |

## Pilot scorecard (baseline first; do not invent targets)

Track weekly:
1. New prospects researched.
2. Prospects with evidence-backed product/buyer fit.
3. Drafts approved / held / rejected.
4. Qualified RFQs received.
5. RFQs complete on first pass.
6. Time from enquiry to acknowledgement and complete quote.
7. Quotes issued, follow-ups completed, orders won/lost.
8. Win/loss reasons and gross margin where authorized.
9. Qualified opportunities and orders by product family and lead source.
10. Claims corrected because evidence was missing or stale.

The first two weeks should establish baseline rates. Set numerical targets after the baseline and sales-owner review.

## Decision gate before building

Build or integrate a component only if:
- A named revenue workflow is failing.
- The failure can be observed in the scorecard or reproduced in a test.
- Harvey's native capability and existing company tools cannot solve it through configuration.
- A proven component has been evaluated for fit, price, security, data ownership and exit path.
- The integration has a human approval boundary and can be rolled back.
