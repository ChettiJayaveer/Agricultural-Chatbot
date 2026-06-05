$(document).ready(function() {
    // --- 1. INITIALIZATION ---
    // Load initial data for the city currently in the sidebar input
    let initialCity = $("#city-selector").val() || "Kakinada"; 
    loadDashboard(initialCity);

    // --- 2. DYNAMIC CITY INPUT HANDLER ---
    // Updates the 5-hour forecast and mandi prices when you press 'Enter'
    $("#city-selector").on("keypress", function(e) {
        if(e.which == 13) { // 13 is the Enter key
            var newCity = $(this).val().trim();
            if(newCity) {
                loadDashboard(newCity);
            }
        }
    });

    // --- 3. CHAT LOGIC (USER & BOT) ---
    $("#messageArea").on("submit", function(event) {
        event.preventDefault();
        
        var rawText = $("#text").val().trim();
        if (rawText === "") return;

        // User Message: Aligned Right (Curved Rectangle)
        var userHtml = '<div class="chat-bubble user-bubble">' + rawText + '</div>';
        $("#text").val("");
        $("#messageFormeight").append(userHtml);
        scrollToBottom();

        // Send to Flask Backend (/ask route)
        $.ajax({
            data: { messageText: rawText },
            type: "POST",
            url: "/ask",
        }).done(function(data) {
            // Bot Message: Aligned Left
            var botHtml = '<div class="chat-bubble bot-bubble">' + data.answer + '</div>';
            $("#messageFormeight").append(botHtml);
            
            // Automatically read the AI response aloud
            speak(data.answer);
            
            scrollToBottom();
        });
    });

    // --- 4. VOICE-TO-TEXT (MICROPHONE) ---
    const voiceBtn = document.getElementById('voice-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-IN'; // Optimized for Indian English
        recognition.continuous = false;

        voiceBtn.addEventListener('click', () => {
            recognition.start();
            voiceBtn.style.color = "#D4AF37"; // Turn icon Gold while listening
        });

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            $("#text").val(transcript); // Type into the long text box
            voiceBtn.style.color = ""; 
        };

        recognition.onend = () => { voiceBtn.style.color = ""; };
        recognition.onerror = () => { voiceBtn.style.color = ""; };
    }

    // --- 5. TEXT-TO-SPEECH (AUDIO LISTENING) ---
    const stopBtn = document.getElementById('stop-speech');

    function speak(text) {
        window.speechSynthesis.cancel(); // Stop any existing audio
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Control the 'Stop/Mute' button visibility
        utterance.onstart = () => { if(stopBtn) stopBtn.style.display = "flex"; };
        utterance.onend = () => { if(stopBtn) stopBtn.style.display = "none"; };
        
        window.speechSynthesis.speak(utterance);
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', () => {
            window.speechSynthesis.cancel();
            stopBtn.style.display = "none";
        });
    }

    // --- 6. DASHBOARD LOADER (WEATHER & MANDI) ---
    function loadDashboard(city) {
        $.get("/get_dashboard?city=" + city, function(data) {
            
            // A. Populate Hourly Forecast (Medium Sidebar Section)
            let weatherHtml = "";
            if (data.forecast && data.forecast.length > 0) {
                data.forecast.forEach(hour => {
                    weatherHtml += `
                        <div class="weather-card" style="display:inline-block; min-width:85px; text-align:center; margin-right:15px;">
                            <div style="font-size:0.7rem; color:white; opacity:0.8;">${hour.time}</div>
                            <div style="font-weight:bold; color:#D4AF37; margin:4px 0;">${hour.temp}°C</div>
                            <div style="font-size:0.6rem; color:#ccc;">${hour.desc}</div>
                        </div>`;
                });
            } else {
                weatherHtml = "<p style='font-size:0.75rem; color:#888;'>Forecast unavailable.</p>";
            }
            $("#weather-box").html(weatherHtml);

            // B. Populate Mandi Prices (Long Sidebar Section)
            let mandiHtml = "";
            if (data.prices && data.prices.length > 0) {
                data.prices.forEach(record => {
                    mandiHtml += `
                        <div class="mandi-item" style="padding:10px 0; border-bottom:1px solid rgba(255,255,255,0.1);">
                            <div style="font-weight:600; color:white; font-size:0.9rem;">${record.commodity}</div>
                            <div style="color:#D4AF37; font-size:0.8rem;">₹${record.modal_price} / Quintal</div>
                            <div style="font-size:0.65rem; color:#888;">Market: ${record.market}</div>
                        </div>`;
                });
            } else {
                mandiHtml = "<p style='padding:20px; font-size:0.8rem; color:#888;'>No mandi data for this city.</p>";
            }
            $("#mandi-list").html(mandiHtml);
        });
    }

    // --- 7. UTILITIES ---
    function scrollToBottom() {
        var chatContainer = $("#messageFormeight");
        chatContainer.animate({ scrollTop: chatContainer[0].scrollHeight }, 500);
    }
});