const audio_id = document.getElementById("audio");
audio_vol = audio_id.volume;
audio_id.volume = 0.6;

// Separate function to convert seconds into MM:SS format
function formatTime(seconds) {
    return Math.floor(seconds);
}

// Separate function to display the play/pause button
function displayPlayPauseButton() {
    const isPaused = audio_id.paused;
    document.getElementById("audio_play_btn").style.display = isPaused ? "inline-block" : "none";
    document.getElementById("audio_pause_btn").style.display = isPaused ? "none" : "inline-block";
}

// Update audio time and progress bar
audio_id.ontimeupdate = function() {
    const audio_currentTime = audio_id.currentTime;
    const playingPercentage = (audio_currentTime / audio_id.duration) * 100;
    document.getElementsByClassName("audio_bar_now")[0].style.width = `${playingPercentage}%`;
    document.getElementById("audio_current_time").innerHTML = formatTime(audio_currentTime) + " Sec";
    displayPlayPauseButton();
};

// Keyboard shortcuts
document.onkeydown = function(event) {
    if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
        return;
    }

    switch (event.code) {
        case 'ArrowLeft':
            event.preventDefault();
            audio_id.currentTime -= 5;
            break;
        case 'ArrowUp':
            event.preventDefault();
            setVolume(Math.min(audio_id.volume + 0.08, 1));
            break;
        case 'ArrowRight':
            event.preventDefault();
            audio_id.currentTime += 5;
            break;
        case 'ArrowDown':
            event.preventDefault();
            setVolume(Math.max(audio_id.volume - 0.08, 0));
            break;
        case 'Space':
            event.preventDefault();
            audio_id.paused ? audio_id.play() : audio_id.pause();
            break;
    }
};

// Change current play on click
document.getElementById("audio_progress").addEventListener("click", (event) => {
    const bar = document.getElementById("audio_progress");
    const clickPosition = event.clientX - bar.offsetLeft;
    audio_id.currentTime = (clickPosition / bar.offsetWidth) * audio_id.duration;
});

function setVolume(volume) {
    audio_id.volume = volume;
    document.getElementById("volumeSlider").style.color = volume === 0 ? "#ff8935" : "#fff";
    document.getElementById("volumeSlider").value = volume;
}

document.getElementById("volumeSlider").addEventListener("input", function(event) {
    setVolume(event.target.value);
});

// Play and pause button controls
document.getElementById("audio_play_btn").addEventListener("click", function() {
    audio_id.play();
    displayPlayPauseButton();
});

document.getElementById("audio_pause_btn").addEventListener("click", function() {
    audio_id.pause();
    displayPlayPauseButton();
});
