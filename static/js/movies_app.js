const grid = document.getElementById("movie-grid");
const searchInput = document.getElementById("movie-search");
const catalogCount = document.getElementById("catalog-count");

let allMovies = [];
let currentMovie = null;

initializePage();

async function initializePage() {
  attachKeyboardShortcuts();
  attachSearchListener();
  await loadMovies();
}

function attachKeyboardShortcuts() {
  document.addEventListener(
    "keydown",
    (event) => {
      const activeVideo = document.getElementById("main-video");
      if (!activeVideo) {
        return;
      }

      if (event.code === "Space") {
        event.preventDefault();
        togglePlay();
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        activeVideo.currentTime += 10;
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        activeVideo.currentTime -= 10;
      }
    },
    true,
  );
}

function attachSearchListener() {
  searchInput.addEventListener("input", () => {
    displayMovies(getFilteredMovies(searchInput.value));
  });
}

async function loadMovies() {
  const response = await fetch("/get-movies");
  allMovies = await response.json();
  updateCatalogCount(allMovies.length);
  displayMovies(allMovies);
  window.setInterval(refreshMoviesIfChanged, 30000);
}

async function refreshMoviesIfChanged() {
  try {
    const response = await fetch("/get-movies");
    if (!response.ok) {
      return;
    }

    const latestMovies = await response.json();
    if (JSON.stringify(latestMovies) === JSON.stringify(allMovies)) {
      return;
    }

    allMovies = latestMovies;
    if (!currentMovie && !grid.classList.contains("player-mode")) {
      displayMovies(getFilteredMovies(searchInput.value));
    }
  } catch (error) {
    console.warn("Could not refresh the catalog list:", error);
  }
}

function getFilteredMovies(searchTerm) {
  const term = searchTerm.toLowerCase();
  return allMovies.filter((movie) =>
    movie.display_name.toLowerCase().includes(term),
  );
}

function displayMovies(moviesToDisplay) {
  currentMovie = null;
  grid.classList.remove("player-mode");
  grid.innerHTML = "";
  updateCatalogCount(
    moviesToDisplay.length,
    moviesToDisplay.length === allMovies.length
      ? "titles available"
      : "matching results",
  );

  moviesToDisplay.forEach((movie) => {
    grid.appendChild(createMovieCard(movie));
  });
}

function createMovieCard(movie) {
  const card = document.createElement("div");
  card.className = "movie-card minimal-card";

  let thumbHtml = "";
  if (movie.thumbnail) {
    const filename = movie.thumbnail.split("\\").pop().split("/").pop();
    thumbHtml = `<div class="image-wrapper"><img src="/static/thumbnails/${filename}" class="movie-thumbnail" alt="${movie.display_name} Poster" loading="lazy" /></div>`;
  } else {
    const initial = movie.display_name.charAt(0).toUpperCase();
    thumbHtml = `
      <div class="image-wrapper thumbnail-fallback">
        <span class="fallback-initial">${initial}</span>
      </div>
    `;
  }

  card.innerHTML = `
    ${thumbHtml}
    <div class="movie-card-content minimal-content">
        <h3>${movie.display_name}</h3>
        <p>${movie.year || "Unknown"}</p>
    </div>
  `;

  // 3D Parallax Hover Effect
  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const xPct = x / rect.width - 0.5;
    const yPct = y / rect.height - 0.5;
    card.style.transform = `perspective(1000px) rotateX(${-yPct * 15}deg) rotateY(${xPct * 15}deg) scale3d(1.05, 1.05, 1.05)`;
    card.style.setProperty("--glare-x", `${(x / rect.width) * 100}%`);
    card.style.setProperty("--glare-y", `${(y / rect.height) * 100}%`);
  });

  card.addEventListener("mouseleave", () => {
    card.style.transform = `perspective(1000px) rotateX(0) rotateY(0) scale3d(1, 1, 1)`;
    card.style.setProperty("--glare-x", `50%`);
    card.style.setProperty("--glare-y", `50%`);
  });

  card.onclick = async () => {
    try {
      if (movie.type === "Video") {
        currentMovie = null;
        const fileName = movie.full_path.split(/[\\/]/).pop();
        renderVideoPlayer(movie, fileName);
        return;
      }

      const files = await fetchFolderContents(movie.full_path);
      renderFolderContents(movie, files);
    } catch (error) {
      alert(
        `Script crashed while opening ${movie.display_name}!\n\n${error.message}\n${error.stack}`,
      );
    }
  };

  return card;
}

async function fetchFolderContents(folderPath) {
  const response = await fetch(
    `/list-contents?path=${encodeURIComponent(folderPath)}`,
  );
  const data = await response.json();
  return data.files || [];
}

function renderFolderContents(movie, files) {
  currentMovie = movie;
  grid.classList.remove("player-mode");

  let castHtml = "";
  if (movie.cast_list) {
    try {
      const castArray = JSON.parse(movie.cast_list);
      let castCardsHtml = "";
      castArray.forEach((c) => {
        let imgTag = c.image
          ? `<img src="/static/cast/${c.image}" class="cast-photo" alt="${c.name}" loading="lazy" />`
          : `<div class="cast-photo-fallback">${c.name.charAt(0).toUpperCase()}</div>`;

        castCardsHtml += `
          <div class="cast-member">
            ${imgTag}
            <span class="cast-name">${c.name}</span>
            <span class="cast-role">${c.role}</span>
          </div>
        `;
      });

      if (castCardsHtml) {
        castHtml = `
          <div class="detail-cast-section">
            <h3 class="cast-section-title">Cast</h3>
            <div class="cast-row">
              ${castCardsHtml}
            </div>
          </div>
        `;
      }
    } catch (e) {}
  }

  let thumbHtml = "";
  if (movie.thumbnail) {
    const filename = movie.thumbnail.split("\\").pop().split("/").pop();
    thumbHtml = `<img src="/static/thumbnails/${filename}" class="detail-thumbnail" alt="${movie.display_name} Poster" />`;

    extractAverageColor(`/static/thumbnails/${filename}`, (color) => {
      const detailView = document.querySelector(".movie-detail-view");
      if (detailView) {
        detailView.style.setProperty("--movie-theme", color);
      }
    });
  } else {
    const initial = movie.display_name.charAt(0).toUpperCase();
    thumbHtml = `
      <div class="detail-thumbnail thumbnail-fallback-detail">
        <span class="fallback-initial">${initial}</span>
      </div>
    `;
  }

  let bgHtml = "";
  if (movie.backdrop) {
    const bgFilename = movie.backdrop.split("\\").pop().split("/").pop();
    bgHtml = `<div class="detail-backdrop" style="background-image: url('/static/thumbnails/${bgFilename}')"></div>`;
  }

  const runtimeText = movie.runtime
    ? `${Math.floor(movie.runtime / 60)} hr ${movie.runtime % 60} min`
    : "";

  const detailsHtml = `
    <div class="movie-detail-view">
        ${bgHtml}
        <div class="detail-overlay"></div>
        <div class="detail-flex">
            ${thumbHtml}
            <div class="detail-content">
                <h2 class="catalog-section-title">${movie.display_name}</h2>
                ${movie.tagline ? `<p class="detail-tagline">"${movie.tagline}"</p>` : ""}
                
                <div class="detail-meta">
                    ${movie.community_rating ? `<span class="rating-star">★ ${movie.community_rating.toFixed(1)}</span>` : ""}
                    ${movie.official_rating ? `<span class="movie-badge cert-badge">${movie.official_rating}</span>` : ""}
                    <span class="movie-badge">${movie.year || "Unknown"}</span>
                    ${runtimeText ? `<span class="movie-badge runtime">${runtimeText}</span>` : ""}
                </div>
                
                ${movie.synopsis ? `<p class="detail-synopsis">${movie.synopsis}</p>` : ""}
                ${movie.genres ? `<p class="detail-genres"><strong>Genres:</strong> ${movie.genres}</p>` : ""}
                ${castHtml}
            </div>
        </div>
    </div>
  `;

  grid.innerHTML = "";

  const topToolbar = document.createElement("div");
  topToolbar.className = "top-back-toolbar";
  topToolbar.appendChild(createResultsBackButton());
  grid.appendChild(topToolbar);

  grid.insertAdjacentHTML("beforeend", detailsHtml);
  updateCatalogCount(files.length, "items in folder");

  const contentSection = document.createElement("div");
  contentSection.className = "folder-contents-section";

  files.forEach((fileName) => {
    contentSection.appendChild(createFileItem(movie, fileName));
  });

  grid.appendChild(contentSection);
}

function createResultsBackButton() {
  const backBtn = document.createElement("button");
  backBtn.className = "catalog-back-link";
  backBtn.innerText = "Back to Results";
  backBtn.onclick = () => {
    displayMovies(getFilteredMovies(searchInput.value));
  };
  return backBtn;
}

function createFileItem(movie, fileName) {
  const fileItem = document.createElement("div");
  fileItem.className = "file-item";
  fileItem.innerText = fileName;

  if (isVideoFile(fileName)) {
    fileItem.classList.add("video-file");
    fileItem.onclick = () => {
      renderVideoPlayer(movie, fileName);
    };
  }

  return fileItem;
}

function renderVideoPlayer(movie, fileName) {
  const videoPath =
    movie.type === "Video"
      ? movie.full_path
      : `${movie.full_path}\\${fileName}`;
  const videoUrl = `/stream-video?path=${encodeURIComponent(videoPath)}`;
  const videoType = getVideoMimeType(fileName);

  grid.classList.add("player-mode");
  updateCatalogCount(fileName, "now playing");
  grid.innerHTML = `
    <div class="video-container premium-player" id="video-container">
      <video id="main-video" autoplay>
        <source src="${videoUrl}" type="${videoType}">
        Your browser could not play this video directly.
      </video>
      
      <div id="premium-controls" class="premium-controls">
        <div class="pc-top">
           <button id="close-player" class="pc-btn catalog-back-link">← Back to Files</button>
           <h2 class="pc-title">${fileName}</h2>
        </div>
        
        <div class="pc-center" id="pc-center">
           <button id="pc-center-play" class="pc-huge-btn">▶</button>
        </div>
        
        <div class="pc-bottom">
           <div class="pc-progress-container">
              <input type="range" id="pc-progress" value="0" min="0" max="100" class="pc-progress" />
              <div id="pc-progress-fill" class="pc-progress-fill"></div>
           </div>
           
           <div class="pc-row">
              <button id="pc-play" class="pc-btn">⏸</button>
              <div class="pc-time"><span id="pc-current">0:00</span> / <span id="pc-total">0:00</span></div>
              <div class="pc-vol-container">
                <button id="pc-mute" class="pc-btn">🔊</button>
                <input type="range" id="pc-volume" value="1" min="0" max="1" step="0.05" class="pc-volume" />
              </div>
              <button id="pc-fullscreen" class="pc-btn">⛶</button>
           </div>
        </div>
      </div>
    </div>
  `;

  // --- Attach Player Logic ---
  const video = document.getElementById("main-video");
  const container = document.getElementById("video-container");
  const playBtn = document.getElementById("pc-play");
  const centerPlay = document.getElementById("pc-center-play");
  const progSlider = document.getElementById("pc-progress");
  const progFill = document.getElementById("pc-progress-fill");
  const volSlider = document.getElementById("pc-volume");
  const muteBtn = document.getElementById("pc-mute");
  const fsBtn = document.getElementById("pc-fullscreen");
  const tCur = document.getElementById("pc-current");
  const tTot = document.getElementById("pc-total");
  const controls = document.getElementById("premium-controls");

  document.getElementById("close-player").onclick = async () => {
    document.removeEventListener("keydown", keyHandler);
    if (document.fullscreenElement) document.exitFullscreen();
    if (!currentMovie) {
      displayMovies(getFilteredMovies(searchInput.value));
      return;
    }
    const files = await fetchFolderContents(currentMovie.full_path);
    renderFolderContents(currentMovie, files);
  };

  const togglePlay = () => {
    if (video.paused) video.play();
    else video.pause();
  };

  playBtn.onclick = togglePlay;
  centerPlay.onclick = togglePlay;

  const keyHandler = (e) => {
    if (e.code === "Space") {
      e.preventDefault();
      togglePlay();
      showControls();
    }
  };
  document.addEventListener("keydown", keyHandler);

  video.onplay = () => {
    playBtn.innerHTML = "⏸";
    centerPlay.style.display = "none";
  };
  video.onpause = () => {
    playBtn.innerHTML = "▶";
    centerPlay.style.display = "block";
  };

  const formatTime = (s) => {
    if (isNaN(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60)
      .toString()
      .padStart(2, "0");
    return `${m}:${sec}`;
  };

  video.ontimeupdate = () => {
    if (video.duration) {
      const pct = (video.currentTime / video.duration) * 100;
      progSlider.value = pct;
      progFill.style.width = `${pct}%`;
      tCur.innerText = formatTime(video.currentTime);
      tTot.innerText = formatTime(video.duration);
    }
  };

  progSlider.oninput = (e) => {
    video.currentTime = (e.target.value / 100) * video.duration;
  };

  volSlider.oninput = (e) => {
    video.volume = e.target.value;
    video.muted = false;
    muteBtn.innerText = video.volume === 0 ? "🔇" : "🔊";
  };

  muteBtn.onclick = () => {
    video.muted = !video.muted;
    muteBtn.innerText = video.muted ? "🔇" : "🔊";
  };

  fsBtn.onclick = () => {
    if (!document.fullscreenElement) container.requestFullscreen();
    else document.exitFullscreen();
  };

  let fadeTimeout;
  const showControls = () => {
    controls.style.opacity = "1";
    container.style.cursor = "default";
    clearTimeout(fadeTimeout);
    fadeTimeout = setTimeout(() => {
      if (!video.paused) {
        controls.style.opacity = "0";
        container.style.cursor = "none";
      }
    }, 2500);
  };

  container.onmousemove = showControls;
  container.addEventListener("click", (e) => {
    if (
      e.target.tagName !== "BUTTON" &&
      e.target.tagName !== "INPUT" &&
      !e.target.closest("button")
    ) {
      togglePlay();
    }
    showControls();
  });
}

function isVideoFile(fileName) {
  return /\.(avi|m2ts|m4v|mkv|mov|mp4|mpeg|mpg|ts|webm|wmv)$/i.test(fileName);
}

function getVideoMimeType(fileName) {
  const lowerName = fileName.toLowerCase();

  if (lowerName.endsWith(".mp4")) {
    return "video/mp4";
  }

  if (lowerName.endsWith(".mkv")) {
    return "video/x-matroska";
  }

  if (lowerName.endsWith(".webm")) {
    return "video/webm";
  }

  if (lowerName.endsWith(".mov") || lowerName.endsWith(".m4v")) {
    return "video/mp4";
  }

  if (lowerName.endsWith(".avi")) {
    return "video/x-msvideo";
  }

  if (lowerName.endsWith(".wmv")) {
    return "video/x-ms-wmv";
  }

  if (/\.(m2ts|mpeg|mpg|ts)$/i.test(fileName)) {
    return "video/mp2t";
  }

  return "";
}

function updateCatalogCount(value, label = "titles available") {
  if (!catalogCount) {
    return;
  }

  catalogCount.textContent = `${value} ${label}`;
}

// --- Utility Functions ---

function extractAverageColor(imgSrc, callback) {
  const img = new Image();
  img.crossOrigin = "Anonymous";
  img.src = imgSrc;
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = 5;
    canvas.height = 5;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, 5, 5);
    try {
      const data = ctx.getImageData(0, 0, 5, 5).data;
      let r = 0,
        g = 0,
        b = 0;
      for (let i = 0; i < data.length; i += 4) {
        r += data[i];
        g += data[i + 1];
        b += data[i + 2];
      }
      const count = data.length / 4;
      callback(
        `rgb(${Math.round(r / count)}, ${Math.round(g / count)}, ${Math.round(b / count)})`,
      );
    } catch (e) {
      callback("transparent");
    }
  };
  img.onerror = () => callback("transparent");
}
