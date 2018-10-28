#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from util import *
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

FEATS = (
    "duration_ms",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature"
)


class SpotifyWrapper(object):

    def __init__(self, client_creds, albums):

        iprint("Setting up Spotify client")
        self.sp = Spotify(
            client_credentials_manager=SpotifyClientCredentials(*client_creds))
        self.sp.trace = False

        # Sqpotify API endpoint limits
        self.MAX_ALBUMS = 20
        self.MAX_AUDIO_FEATS = 100
        self.MAX_SEARCH = 50

        self.albums = albums
        self.table = []
        self.data = []

    def get_table(self):

        return self.table

    def get_albums_uris(self):

        iprint("Getting album URIs")
        for album_ix, album in enumerate(self.albums):
            resp = self.sp.search(
                q="album:{} artist:{}".format(*album[1:3]), type="album",
                limit=self.MAX_SEARCH
            )["albums"]

            if resp["total"]:
                self.table.append(
                    (album[1:] + (
                        resp["items"][0]["uri"].replace("spotify:album:", ''), )
                     )
                )
                sprint("Received response for:", " by ".join(album[1:3]))

            else:
                self.table.append((album[1:] + (None, )))
                wprint("No response for:", " by ".join(album[1:3]))

    def get_tracklists_uris(self):

        tracklists = []

        iprint("Getting tracks URIs")
        # increment by MAX_ALBUMS album IDs
        for album_ix in range(0, len(self.table), self.MAX_ALBUMS):
            resp = self.sp.albums(
                [
                    album[-1] for album in
                    self.table[album_ix:album_ix + self.MAX_ALBUMS] if album[-1]
                ]
            )
            # append all the responses
            tracklists.append(resp)

        # flatten tracklist array
        tracklists = [
            item for ll in tracklists if ll for item in ll["albums"]
        ]

        album_ix = 0
        tracks_ix = 0
        while album_ix < len(self.table):
            if self.table[album_ix][-1]:
                self.table[album_ix] = (
                    self.table[album_ix] + (
                        # comma joined URIs
                        ",".join(
                            tracks["uri"].replace("spotify:track:", '')
                            for tracks in
                            tracklists[tracks_ix]["tracks"]["items"]
                        ),
                        # percentage of explicit tracks
                        np.mean(
                            np.array([
                                tracks["explicit"] for tracks in
                                tracklists[tracks_ix]["tracks"]["items"]
                            ])
                        )
                    )
                )
                tracks_ix += 1
            else:
                self.table[album_ix] = self.table[album_ix] + (None, -1.0)
            album_ix += 1

    def __stats(self, feats):

        stats = []
        for attr in FEATS:
            stats.append(np.mean(np.array([resp[attr] for resp in feats])))
            stats.append(np.median(np.array([resp[attr] for resp in feats])))
            stats.append(
                np.min(np.array([np.float64(resp[attr]) for resp in feats])))
            stats.append(
                np.max(np.array([np.float64(resp[attr]) for resp in feats])))

        return tuple(stats)

    def get_tracks_analysis(self):

        iprint("Getting audio analysis on tracks")
        track_uris = ",".join(i[-2] for i in self.table if i[-2]).split(",")

        feats = []
        for uri_ix in range(0, len(track_uris), self.MAX_AUDIO_FEATS):
            feats.extend(self.sp.audio_features(
                track_uris[uri_ix:uri_ix + self.MAX_AUDIO_FEATS]))

        uri_ix = 0
        for album_ix in range(len(self.table)):
            album_uris = self.table[album_ix][-2]
            if album_uris:
                n_albums = album_uris.count(",") + 1
                self.table[album_ix] = (
                    self.table[album_ix] +
                    self.__stats(feats[uri_ix:uri_ix + n_albums])
                )
                uri_ix += n_albums
            else:
                self.table[album_ix] = (
                    self.table[album_ix] +
                    (-1.0,) * 4 * len(FEATS)
                )
