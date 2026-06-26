from pydantic import BaseModel


class FilePreview(BaseModel):
    columns_detected: list[str]
    rows_count: int
    issues: list[str]
    preview: list[dict[str, str]]


class ValidateFilesResponse(BaseModel):
    purchases: FilePreview
    sales: FilePreview
