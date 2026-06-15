export function populateModelSelect(select: HTMLSelectElement | null, models: string[], selected: string): void {
  if (!select) {
    return;
  }

  const unique = Array.from(new Set(models.filter(Boolean)));
  if (selected && !unique.includes(selected)) {
    unique.unshift(selected);
  }

  const options = unique.map((model) => {
    const option = select.ownerDocument.createElement("option");
    option.value = model;
    option.textContent = model;
    return option;
  });
  select.replaceChildren(...options);

  if (selected) {
    select.value = selected;
  }
}
