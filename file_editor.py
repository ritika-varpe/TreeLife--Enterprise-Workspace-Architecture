import shutil
from pathlib import Path

from openpyxl import load_workbook
from docx import Document


def update_excel_cell(
    input_path: str,
    output_path: str,
    sheet: str,
    cell: str,
    value
):
    """Update a single Excel cell and validate the resulting workbook."""

    input_path = Path(input_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(input_path, output_path)

    workbook = load_workbook(output_path)

    if sheet not in workbook.sheetnames:
        raise ValueError(
            f"Sheet '{sheet}' not found."
        )

    worksheet = workbook[sheet]

    worksheet[cell] = value

    workbook.save(output_path)

    # Validate the saved workbook
    validation_workbook = load_workbook(
        output_path,
        data_only=False
    )

    if sheet not in validation_workbook.sheetnames:
        raise ValueError(
            "Validation failed: sheet missing."
        )

    if validation_workbook[sheet][cell].value != value:
        raise ValueError(
            "Validation failed: cell value was not updated."
        )

    validation_workbook.close()
    workbook.close()

    return {
        "status": "success",
        "operation": "update_cell",
        "sheet": sheet,
        "cell": cell,
        "value": value,
        "output_file": str(output_path)
    }


def replace_word_text(
    input_path: str,
    output_path: str,
    old_text: str,
    new_text: str
):
    """Replace text in a Word document and validate the result."""

    input_path = Path(input_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    document = Document(input_path)

    replacements = 0

    for paragraph in document.paragraphs:

        if old_text in paragraph.text:
            for run in paragraph.runs:
                if old_text in run.text:
                    run.text = run.text.replace(
                        old_text,
                        new_text
                    )
                    replacements += 1

    document.save(output_path)

    # Validate the resulting document
    validation_document = Document(output_path)

    full_text = "\n".join(
        paragraph.text
        for paragraph in validation_document.paragraphs
    )

    validation_document._element.getparent().remove(
        validation_document._element
    )

    if replacements == 0:
        raise ValueError(
            "The specified text was not found."
        )

    if new_text not in full_text:
        raise ValueError(
            "Validation failed: replacement text not found."
        )

    return {
        "status": "success",
        "operation": "replace_text",
        "replacements": replacements,
        "output_file": str(output_path)
    }