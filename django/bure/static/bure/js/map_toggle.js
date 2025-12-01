// bure/static/bure/js/location_toggle.js


document.addEventListener("DOMContentLoaded", function () {
    const modeButtons = document.querySelectorAll(".location-mode-toggle .mode-btn");
    const hiddenModeInput = document.getElementById("location_mode");
    const listModeDiv = document.getElementById("location-list-mode");
    const mapModeDiv = document.getElementById("location-map-mode");
    const mapContainer = document.getElementById("location-map");
    const mapHiddenInputsContainer = document.getElementById("map-location-inputs");

    let leafletMap = null;
    const selectedLocations = new Set();
    const marketByCode = {};

    const defaultStyle = {
        radius: 11,
        color: "#1e3a8a",
        weight: 1,
        fillColor: "#3b82f6",
        fillOpacity: 0.6,
    };

        const selectedStyle = {
        ...defaultStyle,
        radius: 13,
        color: "#b91c1c",
        fillColor: "#f87171",
        weight: 3,
    };

    function syncHiddenInputs() {
        if (!mapHiddenInputsContainer) return;
        mapHiddenInputsContainer.innerHTML = "";
        selectedLocations.forEach((locCode) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "locations";
        input.value = locCode;
        mapHiddenInputsContainer.appendChild(input);
        });
    }



    function initMap() {


        if (!mapContainer || leafletMap || typeof L === "undefined") return;

        leafletMap = L.map(mapContainer).setView([42.35, -71.10], 12);

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                maxZoom: 19,
                attribution: "&copy; OpenStreetMap contributors",
            }
        ).addTo(leafletMap);

        const districts = [
        { code: "allston", label: "Allston", coords: [42.353, -71.132] },
        { code: "brighton", label: "Brighton", coords: [42.347, -71.150] },
        { code: "fenway", label: "Fenway / Kenmore", coords: [42.347, -71.097] },
        { code: "back_bay", label: "Back Bay", coords: [42.35, -71.081] },
        ];

        districts.forEach((d) => {
        const marker = L.circleMarker(d.coords, defaultStyle).addTo(leafletMap);
        marketByCode[d.code] = marker;

        marker.bindTooltip(d.label, { direction: "top" });

        marker.on("click", () => {
            if (selectedLocations.has(d.code)) {
            selectedLocations.delete(d.code);
            marker.setStyle(defaultStyle);
            } else {
            selectedLocations.add(d.code);
            marker.setStyle(selectedStyle);
            }
            syncHiddenInputs();
        });
        });
    }

    if (!hiddenModeInput || !listModeDiv || !mapModeDiv) return;

    modeButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
        const mode = btn.dataset.mode;

        hiddenModeInput.value = mode;
        modeButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        if (mode === "list") { // deselect all districts
            listModeDiv.style.display = "block";
            mapModeDiv.style.display = "none";
            selectedLocations.clear()

            // clear hidden inputs injected by map
            if (mapHiddenInputsContainer) { 
            mapHiddenInputsContainer.innerHTML = "";
            }
            // reset markers back to default style
            Object.values(markerByCode).forEach((marker) => {
            marker.setStyle(defaultStyle);
            });
        } else { // shop map
            listModeDiv.style.display = "none";
            mapModeDiv.style.display = "block";
            initMap();
            setTimeout(() => {
            if (leafletMap) leafletMap.invalidateSize();
            }, 150);

            const listCheckboxes = listModeDiv.querySelectorAll('input[name="locations"]');
            listCheckboxes.forEach((cb) => {
                cb.checked = false;
            });
        }
        });
    });
});
