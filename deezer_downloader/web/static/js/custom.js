
function deezer_download(music_id, type, add_to_playlist, create_zip) {
    $.post(deezer_downloader_api_root + '/download',
        JSON.stringify({ type: type, music_id: parseInt(music_id), add_to_playlist: add_to_playlist, create_zip: create_zip}),
        function(data) {
            if(create_zip == true) {
                text = "You like being offline? You will get a zip file!";
            }
            else if(type == "album") {
                if(add_to_playlist == true) {
                    text = "Good choice! The album will be downloaded and queued to the playlist";
                } else {
                    text = "Good choice! The album will be downloaded.";
                }
            } else {
                if(add_to_playlist == true) {
                    text = "Good choice! The song will be downloaded and queued to the playlist";
                } else {
                    text = "Good choice! The song will be downloaded.";
                }
            }
            $.jGrowl(text, { life: 4000 });
            console.log(data);
    });
}


function play_preview(src) {
    $("#audio_tag").attr("src", src)[0].play();
}

$(document).ready(function() {

    var csvHeaders = [];
    var csvRows = [];

    function parseCsv(text) {
        var rows = [], row = [], field = "", quoted = false;
        text = text.replace(/^\uFEFF/, "");
        for (var i = 0; i < text.length; i++) {
            var character = text[i];
            if (quoted) {
                if (character === '"' && text[i + 1] === '"') { field += '"'; i++; }
                else if (character === '"') quoted = false;
                else field += character;
            } else if (character === '"') quoted = true;
            else if (character === ',') { row.push(field); field = ""; }
            else if (character === '\n' || character === '\r') {
                if (character === '\r' && text[i + 1] === '\n') i++;
                row.push(field); field = "";
                if (row.some(function(value) { return value.length; })) rows.push(row);
                row = [];
            } else field += character;
        }
        row.push(field);
        if (row.some(function(value) { return value.length; })) rows.push(row);
        return rows;
    }

    function guessColumn(words) {
        for (var i = 0; i < csvHeaders.length; i++) {
            var header = csvHeaders[i].toLowerCase();
            if (words.some(function(word) { return header.indexOf(word) !== -1; })) return i.toString();
        }
        return "";
    }

    function populateCsvColumns() {
        ["#csv-artist-column", "#csv-title-column", "#csv-album-column"].forEach(function(id) {
            var select = $(id).empty().append($("<option>").val("").text("Not mapped"));
            csvHeaders.forEach(function(header, index) {
                select.append($("<option>").val(index).text(header || "Column " + (index + 1)));
            });
        });
        $("#csv-artist-column").val(guessColumn(["artist", "performer", "band"]));
        $("#csv-title-column").val(guessColumn(["track", "title", "song"]));
        $("#csv-album-column").val(guessColumn(["album", "release"]));
    }

    function renderCsvPreview() {
        var headRow = $("<tr>").append(
            $("<th>").append($("<input type='checkbox' id='csv-select-all' checked>"))
        );
        csvHeaders.forEach(function(header) { headRow.append($("<th>").text(header)); });
        $("#csv-table thead").empty().append(headRow);
        var body = $("#csv-table tbody").empty();
        csvRows.forEach(function(values, index) {
            var row = $("<tr>");
            row.append($("<td>").append($("<input type='checkbox' class='csv-row-select' checked>").attr("data-row", index)));
            csvHeaders.forEach(function(_, column) { row.append($("<td>").text(values[column] || "")); });
            body.append(row);
        });
        $("#csv-summary").text(csvRows.length + " rows loaded");
        $("#csv-mapping, #csv-controls").show();
    }

    $("#csv-file").change(function(event) {
        var file = event.target.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function(loadEvent) {
            var parsed = parseCsv(loadEvent.target.result);
            if (parsed.length < 2) {
                $.jGrowl("The CSV needs a header and at least one data row", { life: 5000 });
                return;
            }
            csvHeaders = parsed[0];
            csvRows = parsed.slice(1);
            populateCsvColumns();
            renderCsvPreview();
        };
        reader.onerror = function() { $.jGrowl("Could not read that CSV file", { life: 5000 }); };
        reader.readAsText(file);
    });

    $(document).on("change", "#csv-select-all", function() {
        $(".csv-row-select").prop("checked", this.checked);
    });

    function csvDownload(type) {
        var artistColumn = $("#csv-artist-column").val();
        var titleColumn = $("#csv-title-column").val();
        var albumColumn = $("#csv-album-column").val();
        if ((type === "track" && titleColumn === "") || (type === "album" && albumColumn === "")) {
            $.jGrowl("Map the " + (type === "track" ? "track" : "album") + " column first", { life: 5000 });
            return;
        }
        var rows = [];
        $(".csv-row-select:checked").each(function() {
            var source = csvRows[parseInt($(this).attr("data-row"))];
            rows.push({
                artist: artistColumn === "" ? "" : (source[parseInt(artistColumn)] || ""),
                title: titleColumn === "" ? "" : (source[parseInt(titleColumn)] || ""),
                album: albumColumn === "" ? "" : (source[parseInt(albumColumn)] || "")
            });
        });
        if (!rows.length) { $.jGrowl("Select at least one row", { life: 5000 }); return; }
        $.ajax({
            url: deezer_downloader_api_root + "/import/csv",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                type: type, rows: rows,
                add_to_playlist: $("#csv-add-to-playlist").prop("checked"),
                create_zip: type === "album" && $("#csv-create-zip").prop("checked")
            }),
            success: function() {
                $.jGrowl("CSV import queued for " + rows.length + " selected rows", { life: 5000 });
            },
            error: function(xhr) {
                var message = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : "Could not queue CSV import";
                $.jGrowl(message, { life: 5000 });
            }
        });
    }

    $("#csv-download-tracks").click(function() { csvDownload("track"); });
    $("#csv-download-albums").click(function() { csvDownload("album"); });

    if(!show_mpd_features) {
        $("#yt_download_play").hide()
        $("#spotify_download_play").hide()
        $("#deezer_playlist_download_play").hide()
        $("#deezer_favorites_download_play").hide()
    };


    function youtubedl_download(add_to_playlist) {
        $.post(deezer_downloader_api_root + '/youtubedl',
            JSON.stringify({ url: $('#youtubedl-query').val(), add_to_playlist: add_to_playlist }),
            function(data) {
                console.log(data);
                $.jGrowl("As you wish", { life: 4000 });
            });
    }
    
    
    function spotify_playlist_download(add_to_playlist, create_zip) {
        $.post(deezer_downloader_api_root + '/playlist/spotify',
            JSON.stringify({ playlist_name: $('#spotify-playlist-name').val(), 
                             playlist_url: $('#spotify-playlist-url').val(),
                             add_to_playlist: add_to_playlist,
                             create_zip: create_zip}),
            function(data) {
                console.log(data);
                $.jGrowl("As you wish", { life: 4000 });
            });
    }



    function deezer_playlist_download(add_to_playlist, create_zip) {
        $.post(deezer_downloader_api_root + '/playlist/deezer',
            JSON.stringify({ playlist_url: $('#deezer-playlist-url').val(),
                             add_to_playlist: add_to_playlist,
                             create_zip: create_zip}),
            function(data) {
                console.log(data);
                $.jGrowl("As you wish", { life: 4000 });
            });
    }
    

    function deezer_favorites_download(add_to_playlist, create_zip) {
        $.post(deezer_downloader_api_root + '/favorites/deezer',
            JSON.stringify({ user_id: $('#deezer-favorites-userid').val(),
                             add_to_playlist: add_to_playlist,
                             create_zip: create_zip}),
            function(data) {
                console.log(data);
                $.jGrowl("As you wish", { life: 4000 });
            });
    }


    function search(type) {
        const query = $('#songs-albums-query').val();
        if (!query.length) return ;
        deezer_load_list(type, query);
    }

    function deezer_load_list(type, query) {
        $.post(deezer_downloader_api_root + '/search',
            JSON.stringify({ type: type, query: query.toString() }),
            function(data) {
                $("#results > tbody").html("");
                for (var i = 0; i < data.length; i++) {
                    drawTableEntry(data[i], type);
                }
        });
    }

    function drawTableEntry(rowData, mtype) {
        var row = $("<tr>");
        $("#results").append(row); 
        var button_col = $("<td style='text-align: end'>");

        if (mtype === "track" || mtype === "album_track" || mtype === "artist_top") {
            $("#col-title").show();
            $("#col-album").show();
            $("#col-artist").show();
            if (mtype !== "album_track") {
                $("#col-cover").show();
                row.append($("<td><img src='"+rowData.img_url+"' style='cursor: pointer; border-radius: 3px'></td>")
                    .click(() => play_preview(rowData.preview_url)));
            } else {
                $("#col-cover").hide();
            }
            row.append($("<td>" + rowData.artist + "</td>"));
            row.append($("<td>" + rowData.title + "</td>"));
            row.append($("<td>" + rowData.album + "</td>"));
            if (rowData.preview_url) {
                button_col.append($('<button class="btn btn-default"> <i class="fa fa-headphones fa-lg" title="listen preview in browser" ></i> </button>')
                    .click(() => play_preview(rowData.preview_url)));
            }
        } else if (mtype === "album" || mtype === "artist_album") {
            $("#col-cover").show();
            $("#col-title").hide();
            $("#col-album").show();
            $("#col-artist").show();
            row.append($("<td><img src='"+rowData.img_url+"' style='cursor: pointer; border-radius: 3px'></td>")
                .click(() => deezer_load_list("album_track", rowData.album_id)));
            row.append($("<td>" + rowData.artist + "</td>"));
            row.append($("<td>" + rowData.album + "</td>"));
            button_col.append($('<button class="btn btn-default"> <i class="fa fa-list fa-lg" title="list album songs" ></i> </button>')
                .click(() => deezer_load_list("album_track", rowData.album_id)));
        } else if (mtype === "artist") {
            $("#col-cover").show();
            $("#col-artist").show();
            $("#col-album").hide();
            $("#col-title").hide();
            row.append($("<td><img src='"+rowData.img_url+"' style='cursor: pointer; border-radius: 29px'></td>")
                .click(() => deezer_load_list("artist_album", rowData.artist_id)));
            row.append($("<td>" + rowData.artist + "</td>"));
            button_col.append($('<button class="btn btn-default"> <i class="fa fa-arrow-up fa-lg" title="list artist top songs" ></i> </button>')
                .click(() => deezer_load_list("artist_top", rowData.artist_id)));
            button_col.append($('<button class="btn btn-default"> <i class="fa fa-list fa-lg" title="list artist albums" ></i> </button>')
                .click(() => deezer_load_list("artist_album", rowData.artist_id)));
        }
        

        if (mtype !== "artist") {
            if (show_mpd_features) {
                button_col.append($('<button class="btn btn-default"> <i class="fa fa-play-circle fa-lg" title="download and queue to mpd" ></i> </button>')
                    .click(() => deezer_download(rowData.id, rowData.id_type, true, false)));
            }
            button_col.append($('<button class="btn btn-default" > <i class="fa fa-download fa-lg" title="download" ></i> </button>')
                .click(() => deezer_download(rowData.id, rowData.id_type, false, false)));
        }

        if(rowData.id_type == "album") {
            button_col.append($('<button class="btn btn-default"> <i class="fa fa-file-archive-o fa-lg" title="download as zip file" ></i> </button>')
            .click(() => deezer_download(rowData.id, rowData.id_type, false, true)));
        }
        row.append(button_col);
    }

    function show_debug_log() {
        $.get(deezer_downloader_api_root + '/debug', function(data) {
            var debug_log_textarea = $("#ta-debug-log");
            debug_log_textarea.val(data.debug_msg);
            if(debug_log_textarea.length) {
                debug_log_textarea.scrollTop(debug_log_textarea[0].scrollHeight - debug_log_textarea.height());
            }
        });
    }

    function show_task_queue() {
        $.get(deezer_downloader_api_root + '/queue', function(data) {
            var queue_table = $("#task-list tbody");
            queue_table.html("");
            
            for (var i = data.length - 1; i >= 0; i--) {
                var html="<tr><td>"+data[i].description+"</td><td>"+JSON.stringify(data[i].args)+"</td>"+
                "<td>"+data[i].state+"</td></tr>";
                $(html).appendTo(queue_table);
                switch (data[i].state) {
                case "active":
                    $("<tr><td colspan=4><progress value="+data[i].progress[0]+" max="+data[i].progress[1]+" style='width:100%'/></td></tr>").appendTo(queue_table);
                case "failed":
                    $("<tr><td colspan=4 style='color:red'>"+data[i].exception+"</td></tr>").appendTo(queue_table);
                }
            }
            if ($("#nav-task-queue").hasClass("active")) {
                setTimeout(show_task_queue, 1000);
            }
        });
    }

    let search_type = "track";
    $("#search_deezer").click(function() {
        search(search_type);
    });

    $("#deezer-search-track").click(function() {
        if (search_type == "track") return;
        search_type = "track";
        $("#deezer-search-track").addClass("active");
        $("#deezer-search-album").removeClass("active");
        $("#deezer-search-artist").removeClass("active");
        search(search_type);
    });

    $("#deezer-search-album").click(function() {
        if (search_type == "album") return;
        search_type = "album";
        $("#deezer-search-album").addClass("active");
        $("#deezer-search-track").removeClass("active");
        $("#deezer-search-artist").removeClass("active");
        search(search_type);
    });

    $("#deezer-search-artist").click(function() {
        if (search_type == "artist") return;
        search_type = "artist";
        $("#deezer-search-artist").addClass("active");
        $("#deezer-search-track").removeClass("active");
        $("#deezer-search-album").removeClass("active");
        search(search_type);
    });

    
    $("#yt_download").click(function() {
        youtubedl_download(false);
    });
    
    $("#yt_download_play").click(function() {
        youtubedl_download(true);
    });
    
    $("#nav-debug-log").click(function() {
        show_debug_log();
    });

    $("#nav-task-queue").click(function() {
        show_task_queue();
    });

    // BEGIN SPOTIFY
    $("#spotify_download_play").click(function() {
        spotify_playlist_download(true, false);
    });

    $("#spotify_download").click(function() {
        spotify_playlist_download(false, false);
    });

    $("#spotify_zip").click(function() {
        spotify_playlist_download(false, true);
    });
    // END SPOTIFY

    
    // BEGIN DEEZER PLAYLIST
    $("#deezer_playlist_download_play").click(function() {
        deezer_playlist_download(true, false);
    });

    $("#deezer_playlist_download").click(function() {
        deezer_playlist_download(false, false);
    });

    $("#deezer_playlist_zip").click(function() {
        deezer_playlist_download(false, true);
    });
    // END DEEZER PLAYLIST

    // BEGIN DEEZER FAVORITE SONGS
    $("#deezer_favorites_download_play").click(function() {
        deezer_favorites_download(true, false);
    });

    $("#deezer_favorites_download").click(function() {
        deezer_favorites_download(false, false);
    });

    $("#deezer_favorites_zip").click(function() {
        deezer_favorites_download(false, true);
    });
    // END DEEZER FAVORITE SONGS


    function show_tab(id_nav, id_content) {
    // nav 
    $(".nav-link").removeClass("active")
    //$("#btn-show-debug").addClass("active")
    $("#" + id_nav).addClass("active")

    // content
    $(".container .tab-pane").removeClass("active show")
    //$("#youtubedl").addClass("active show")
    $("#" + id_content).addClass("active show")
    }


    var bbody = document.getElementById('body');
    bbody.onkeydown = function (event) {
        if (event.key !== undefined) {
           if (event.key === 'Enter' && $("#nav-songs-albums").hasClass("active")) {
               search(search_type);
           } else if (event.key === 'm' && event.ctrlKey) {
              $("#songs-albums-query")[0].value = "";
              $("#songs-albums-query")[0].focus();
           }
           if (event.ctrlKey && event.shiftKey) {
               var tabs = {
                   Digit1: ["nav-songs-albums", "songs_albums"],
                   Digit2: ["nav-youtubedl", "youtubedl"],
                   Digit3: ["nav-spotify-playlists", "spotify-playlists"],
                   Digit4: ["nav-deezer", "deezer"],
                   Digit5: ["nav-csv-import", "csv-import"],
                   Digit7: ["nav-debug-log", "debug"],
                   Digit8: ["nav-task-queue", "queue"]
               };
               if (event.code === "Digit6") window.open('downloads/', '_blank');
               else if (tabs[event.code]) {
                   show_tab(tabs[event.code][0], tabs[event.code][1]);
                   if (event.code === "Digit7") show_debug_log();
                   if (event.code === "Digit8") show_task_queue();
               }
           }
        }
            
    };
});
