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
                width: presentation.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                wrapMode: Text.WordWrap
                color: presentation.bodyText
                text: qsTr("Welcome to aptosid nemesis.<br/>" +
                           "The rest of the installation is automated and will complete in a few minutes.")
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
                    source: "unstreaked-fred-light.png"
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
                text: qsTr("aptosid rides Debian's unstable branch — updated continuously. " +
                           "Install once; no reinstalls, no waiting for the next big release.")
            }
        }
    }

    // Slide 3 - the pitch (little-fred)
    Slide {
        Column {
            anchors.centerIn: parent
            spacing: 18
            Image {
                source: "little-fred-light.png"
                height: 120
                fillMode: Image.PreserveAspectFit
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                font.pointSize: 16; font.bold: true
                color: presentation.accent
                text: qsTr("Bleeding edge, minus the bleeding")
            }
            Text {
                width: presentation.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                wrapMode: Text.WordWrap
                color: presentation.bodyText
                text: qsTr("All the thrill of the front line, with the sharp bits filed off. Mostly.")
            }
        }
    }

    // Slide 4 - sign-off
    Slide {
        Column {
            anchors.centerIn: parent
            spacing: 18
            Image {
                source: "aptosid-icon.png"
                width: 96; height: 96
                fillMode: Image.PreserveAspectFit
                anchors.horizontalCenter: parent.horizontalCenter
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
                font.pointSize: 16; font.bold: true
                color: presentation.accent
                text: qsTr("Welcome to the dark side")
            }
            Text {
                width: presentation.width * 0.8
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.Center
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
