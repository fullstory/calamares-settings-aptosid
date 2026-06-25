/* === This file is part of Calamares - <http://github.com/calamares> ===
 *
 *   Copyright 2015, Teo Mrnjavac <teo@kde.org>
 *   Copyright 2018-2019, Jonathan Carter <jcc@debian.org>
 *   Copyright 2024-2026, Kel Modderman <kelvmod@gmail.com>
 *
 *   Calamares is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, or (at your option) any later version.
 *
 *   Calamares is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Calamares. If not, see <http://www.gnu.org/licenses/>.
 */

import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    // Breeze-dark palette: dark backdrop, light body text, and a brightened
    // aptosid teal for headings so it reads on the dark background.
    property color accent:   "#1abc9c"
    property color bodyText: "#eff0f1"

    // Dark backdrop behind every slide, matching Breeze Dark. It is not a
    // Slide, so the Presentation never hides it; z:-1 keeps it behind the
    // (transparent) slides.
    Rectangle {
        anchors.fill: parent
        color: "#232629"
        z: -1
    }

    // Auto-advance, but only while this slideshow is the active page in
    // Calamares (activatedInCalamares); the timer is otherwise stopped.
    Timer {
        id: advanceTimer
        interval: 15000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    // Slide 1 - welcome
    Slide {
        Column {
            anchors.centerIn: parent
            spacing: 24
            Image {
                source: "aptosid2.png"
                width: 467; height: 280
                fillMode: Image.PreserveAspectFit
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                font.pointSize: 16; font.bold: true
                color: presentation.accent
                text: qsTr("Strap in, Fred's got this")
            }
            Text {
                width: presentation.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                wrapMode: Text.WordWrap
                color: presentation.bodyText
                text: qsTr("Fully automated — blink and you'll miss it.")
            }
        }
    }

    // Slide 2 - rolling / bleeding edge (fred in motion: sharp fred layered
    // over his motion streaks; both share a canvas so they overlay 1:1)
    Slide {
        Column {
            anchors.centerIn: parent
            spacing: 18
            Item {
                width: 181; height: 300   // 217:360 aspect of the fred canvas
                anchors.horizontalCenter: parent.horizontalCenter
                Image {
                    anchors.fill: parent
                    source: "streaked-fred.png"
                    fillMode: Image.PreserveAspectFit
                }
                Image {
                    anchors.fill: parent
                    source: "unstreaked-fred.png"
                    fillMode: Image.PreserveAspectFit
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                font.pointSize: 16; font.bold: true
                color: presentation.accent
                text: qsTr("Flat out on sid")
            }
            Text {
                width: presentation.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                wrapMode: Text.WordWrap
                color: presentation.bodyText
                text: qsTr("One install, updated forever. Fred doesn't do reinstalls.")
            }
        }
    }

    // Slide 3 - the pitch (fred world map)
    Slide {
        Column {
            anchors.centerIn: parent
            spacing: 18
            Image {
                source: "fred-world.png"
                height: 260
                fillMode: Image.PreserveAspectFit
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                font.pointSize: 16; font.bold: true
                color: presentation.accent
                text: qsTr("Resistance is Fred-ile")
            }
            Text {
                width: presentation.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                wrapMode: Text.WordWrap
                color: presentation.bodyText
                text: qsTr("You will be assimilated.")
            }
        }
    }

    // Slide 4 - sign-off: big Fred lunges out of the bottom-right corner
    // (oversized + anchored past the edge so his cropped edges run off-slide),
    // with the wordmark + tagline in the open upper-left. clip keeps the
    // overspill inside the slide. Tune the margins/sizes to taste.
    Slide {
        clip: true

        Image {
            source: "big-fred.png"
            height: parent.height * 1.15
            fillMode: Image.PreserveAspectFit
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: -parent.width * 0.08
            anchors.bottomMargin: -parent.height * 0.08
        }

        Column {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: parent.width * 0.08
            anchors.topMargin: parent.height * 0.14
            spacing: 16

            Image {
                source: "aptosid.png"
                width: presentation.width * 0.46
                fillMode: Image.PreserveAspectFit
            }
            Text {
                horizontalAlignment: Text.AlignLeft
                font.pointSize: 16; font.bold: true
                color: presentation.accent
                text: qsTr("Welcome to the dark side")
            }
            Text {
                width: presentation.width * 0.42
                horizontalAlignment: Text.AlignLeft
                wrapMode: Text.WordWrap
                color: presentation.bodyText
                text: qsTr("Docs and source code at github.com/fullstory.")
            }
        }
    }

    // V2 lifecycle: restart from the first slide each time the page is shown.
    function onActivate() {
        presentation.currentSlide = 0;
    }

    function onLeave() {
    }
}
