"""Bulk-import parsing + fuzzy header-matching tests.

These are pure functions (no DB), so they're fast and deterministic. They lock
in the column-matching behaviour promised in the import spec.
"""

import bulk_import


STUDENT_FIELDS = bulk_import.FIELD_SETS["students"]


def test_fuzzy_header_matching_handles_spec_examples():
    headers = ["Student Name", "Father Name", "Mob", "Adm No", "Class", "Section"]
    mapping = bulk_import.match_columns(headers, STUDENT_FIELDS)

    assert mapping["name"] == "Student Name"
    assert mapping["parent_name"] == "Father Name"   # "father name" -> parent_name
    assert mapping["phone"] == "Mob"                 # "mob" -> phone
    assert mapping["admission_number"] == "Adm No"   # "adm no" -> admission_number
    assert mapping["class"] == "Class"
    assert mapping["section"] == "Section"


def test_each_header_consumed_by_at_most_one_field():
    headers = ["Name", "Email", "Phone"]
    mapping = bulk_import.match_columns(headers, STUDENT_FIELDS)
    chosen = list(mapping.values())
    assert len(chosen) == len(set(chosen))  # no header mapped twice


def test_read_csv_and_extract_records():
    csv_bytes = b"Student Name,Father Name,Class,Section\nAarav,Mr Kumar,9,A\nDiya,Mr Sharma,9,B\n"
    headers, rows = bulk_import.read_table("students.csv", csv_bytes)

    assert "Student Name" in headers
    assert len(rows) == 2

    mapping = bulk_import.match_columns(headers, STUDENT_FIELDS)
    records = bulk_import.extract_records(rows, mapping)

    assert records[0]["row"] == 2  # row 1 is the header
    assert records[0]["data"]["name"] == "Aarav"
    assert records[0]["data"]["parent_name"] == "Mr Kumar"
    assert records[1]["data"]["section"] == "B"


def test_blank_rows_are_skipped():
    csv_bytes = b"Name,Class\nAarav,9\n,\n   ,  \nDiya,10\n"
    _headers, rows = bulk_import.read_table("s.csv", csv_bytes)
    assert len(rows) == 2  # the two blank lines are dropped


def test_unsupported_file_type_raises():
    import pytest
    with pytest.raises(ValueError):
        bulk_import.read_table("data.pdf", b"whatever")


def test_unmapped_headers_reported():
    headers = ["Student Name", "Favourite Colour"]
    mapping = bulk_import.match_columns(headers, STUDENT_FIELDS)
    unmapped = bulk_import.unmapped_headers(headers, mapping)
    assert "Favourite Colour" in unmapped
