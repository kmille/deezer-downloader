
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
        deezer_load_list(type, $('#songs-albums-query').val());
    }

    function deezer_load_list(type, query) {
        $.post(deezer_downloader_api_root + '/search',
            JSON.stringify({ type: type, query: query }),
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
        row.append($("<td>" + rowData.artist + "</td>"));
        row.append($("<td>" + rowData.title + "</td>"));
        
        row.append("<td><img src='"+rowData.img_url+"'> " + rowData.album + "</a></td>");
        
        if (rowData.preview_url) {
            row.append($('<td> <button class="btn btn-default" onclick="play_preview(\'' + rowData.preview_url + '\');" > <i class="fa fa-headphones fa-lg" title="listen preview in browser" ></i> </button> </td>'));
        }
        
        if (mtype == "album") {
            row.append($('<td> <button class="btn btn-default"> <i class="fa fa-list fa-lg" title="list album songs" ></i> </button> </td>').click(function() {deezer_load_list("album_track", ""+rowData.album_id + "")}));
        }
        
        if(show_mpd_features) {
        row.append($('<td> <button class="btn btn-default" onclick="deezer_download(\'' +
                     rowData.id  + '\', \''+ rowData.id_type +
                     '\', true, false);" > <i class="fa fa-play-circle fa-lg" title="download and queue to mpd" ></i> </button> </td>'));
        }

        row.append($('<td> <button class="btn btn-default" onclick="deezer_download(\'' +
                   rowData.id  + '\', \''+ rowData.id_type + 
                   '\', false, false);" > <i class="fa fa-download fa-lg" title="download" ></i> </button> </td>'));

        if(rowData.id_type == "album") {
            row.append($('<td> <button class="btn btn-default" onclick="deezer_download(\'' +
                       rowData.id  + '\', \''+ rowData.id_type + 
                       '\', false, true);" > <i class="fa fa-file-archive-o fa-lg" title="download as zip file" ></i> </button> </td>'));
        }
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

    $("#search_track").click(function() {
        search("track");
    });

    $("#search_album").click(function() {
        search("album");
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
           if (event.key === 'Enter' && event.altKey) {
               console.log("pressed Enter + ALT");
               search("album");
           }  else if (event.key === 'Enter' ) {
               console.log("pressed Enter");
               search("track");
           } else if (event.key === 'm' && event.ctrlKey) {
              console.log("pressed ctrl m");
              $("#songs-albums-query")[0].value = "";
              $("#songs-albums-query")[0].focus();
           }
           if (event.ctrlKey && event.shiftKey) {
               console.log("pressed ctrl + shift + ..");
               if(event.key === '!') {
                   id_nav = "nav-songs-albums";
                   id_content = "songs_albums";
               }
               if(event.key === '"') {
                   id_nav = "nav-youtubedl";
                   id_content = "youtubedl";
               }
               if(event.key === '§') {
                   id_nav = "nav-spotify-playlists";
                   id_content = "spotify-playlists";
               }
               if(event.key === '$') {
                   id_nav = "nav-deezer-playlists";
                   id_content = "deezer-playlists";
               }
               if(event.key === '%') {
                   id_nav = "nav-songs-albums";
                   id_content = "songs_albums";
                   window.open('/downloads/', '_blank');
               }
               if(event.key === "&") {
                   id_nav = "nav-debug-log";
                   id_content = "debug";
                   show_debug_log();
               }
               if(event.key === '/') {
                   id_nav = "nav-task-queue";
                   id_content = "queue";
               }
               if(typeof id_nav !== 'undefined') {
                   show_tab(id_nav, id_content);
               }
           }
        }
            
    };
});
