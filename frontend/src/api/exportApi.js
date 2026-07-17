import { api } from "./client";

function getFilenameFromHeader(contentDisposition) {
  if (!contentDisposition) {
    return "marketplace-listings.xlsx";
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);

  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const normalMatch = contentDisposition.match(/filename="?([^";]+)"?/i);

  return normalMatch?.[1] || "marketplace-listings.xlsx";
}

async function parseBlobError(error) {
  const responseData = error?.response?.data;

  if (!(responseData instanceof Blob)) {
    return error?.response?.data?.detail || error?.message || "Có lỗi xảy ra";
  }

  try {
    const text = await responseData.text();
    const json = JSON.parse(text);

    return json.detail || "Có lỗi xảy ra";
  } catch {
    return "Có lỗi xảy ra";
  }
}

export async function exportListingsToExcel(payload) {
  try {
    const response = await api.post("/exports/excel", payload, {
      responseType: "blob",
    });

    const filename = getFilenameFromHeader(
      response.headers["content-disposition"],
    );

    const blob = new Blob([response.data], {
      type:
        response.headers["content-type"] ||
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    const objectUrl = URL.createObjectURL(blob);

    const anchor = document.createElement("a");

    anchor.href = objectUrl;
    anchor.download = filename;

    document.body.appendChild(anchor);

    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(objectUrl);

    return {
      exportedRows: response.headers["x-exported-rows"] || null,
      filename,
    };
  } catch (error) {
    const message = await parseBlobError(error);

    throw new Error(message);
  }
}

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
