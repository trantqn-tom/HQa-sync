import { api } from "./client";

/**
 * Lấy tên file từ Content-Disposition.
 */
function getFilenameFromHeader(contentDisposition, fallbackFilename) {
  if (!contentDisposition) {
    return fallbackFilename;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);

  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const normalMatch = contentDisposition.match(/filename="?([^";]+)"?/i);

  return normalMatch?.[1] || fallbackFilename;
}

/**
 * Đọc thông báo lỗi khi API trả về Blob.
 */
async function parseBlobError(error) {
  const responseData = error?.response?.data;

  if (!(responseData instanceof Blob)) {
    return error?.response?.data?.detail || error?.message || "Có lỗi xảy ra";
  }

  try {
    const text = await responseData.text();
    const json = JSON.parse(text);

    return json?.detail || "Có lỗi xảy ra";
  } catch {
    try {
      return await responseData.text();
    } catch {
      return "Có lỗi xảy ra";
    }
  }
}

/**
 * Tạo file download từ response Blob.
 */
function downloadBlob(response, fallbackFilename, fallbackContentType) {
  const filename = getFilenameFromHeader(
    response.headers["content-disposition"],
    fallbackFilename,
  );

  const blob = new Blob([response.data], {
    type:
      response.headers["content-type"] ||
      fallbackContentType ||
      "application/octet-stream",
  });

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");

  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(() => {
    URL.revokeObjectURL(objectUrl);
  }, 1000);

  return {
    filename,
    exportedRows: response.headers["x-exported-rows"] || null,
  };
}

/**
 * Đọc danh sách trường có thể export.
 */
export async function getExportColumns() {
  try {
    const response = await api.get("/exports/columns");

    return response.data;
  } catch (error) {
    throw new Error(
      error?.response?.data?.detail ||
        error?.message ||
        "Không thể đọc danh sách trường export",
    );
  }
}

/**
 * Xuất file Excel.
 */
export async function exportListingsToExcel(payload) {
  try {
    const response = await api.post("/exports/excel", payload, {
      responseType: "blob",
    });

    return downloadBlob(
      response,
      "marketplace-listings.xlsx",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    );
  } catch (error) {
    const message = await parseBlobError(error);

    throw new Error(message);
  }
}

/**
 * Xuất file PDF.
 */
export async function exportListingsToPdf(payload) {
  try {
    const response = await api.post("/exports/pdf", payload, {
      responseType: "blob",
    });

    return downloadBlob(
      response,
      "marketplace-listings.pdf",
      "application/pdf",
    );
  } catch (error) {
    const message = await parseBlobError(error);

    throw new Error(message);
  }
}

/**
 * Kiểm tra Google Sheet đích và danh sách tab.
 */
export async function previewGoogleSheet(spreadsheetUrl) {
  try {
    const response = await api.post("/exports/google-sheet/preview", {
      spreadsheet_url: spreadsheetUrl,
    });

    return response.data;
  } catch (error) {
    throw new Error(
      error?.response?.data?.detail ||
        error?.message ||
        "Không thể kiểm tra Google Sheet",
    );
  }
}

/**
 * Xuất dữ liệu sang Google Sheet.
 */
export async function exportListingsToGoogleSheet(payload) {
  try {
    const response = await api.post("/exports/google-sheet", payload);

    return response.data;
  } catch (error) {
    throw new Error(
      error?.response?.data?.detail ||
        error?.message ||
        "Không thể export Google Sheet",
    );
  }
}
