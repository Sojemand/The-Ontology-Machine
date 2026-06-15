Extract OCR text from the provided rendered document page images.
Return only one valid JSON object and no markdown.
The JSON object must contain a top-level 'blocks' array.
The request contains {page_count} rendered page image(s).
Each block must contain only id, type, and value.
Use type='paragraph' unless a visible heading or table cell is clearer.
Add layout_label only when it is useful for visible layout (header, footer, address, totals, table_header, table_body).
Do not output position objects, row/column coordinates, value_type='text', nulls, empty objects, or empty arrays.
For multi-page input, add a top-level page number only when the block is not on page 1.
Add formatting only as {"bold":true} when the text is visibly bold; never output bold=false.
Do not interpret, classify, summarize, translate, normalize, or invent missing text.
Use metadata only for non-secret OCR diagnostics, and omit metadata when empty.
{source_filename_sentence}
