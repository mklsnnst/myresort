(() => {
  function updateUrlWithTour(tourId) {
    const url = new URL(window.location.href);
    if (tourId) {
      url.searchParams.set("tour", tourId);
    } else {
      url.searchParams.delete("tour");
    }
    // Drop changelist filters etc? Keep other params as-is.
    window.location.href = url.toString();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const tourSelect = document.getElementById("id_tour");
    if (!tourSelect) return;

    // When tour changes, reload page with ?tour=<id> so inline services are filtered.
    tourSelect.addEventListener("change", () => {
      const val = tourSelect.value;
      updateUrlWithTour(val);
    });
  });
})();

