//
//  ContentView.swift
//  ios
//
//  Created by Boerni on 14.04.20.
//  Copyright © 2020 stream-steam. All rights reserved.
//

import SwiftUI
import MatomoTracker


func initTracker() -> MatomoTracker {
    // get tracking server URl from plist
    var resourceFileDictionary: NSDictionary?
    if let path = Bundle.main.path(forResource: "Info", ofType: "plist") {
        resourceFileDictionary = NSDictionary(contentsOfFile: path)
    }

    // actual tracker
    let matomoTracker = MatomoTracker(siteId: "1", baseURL: URL(string: resourceFileDictionary?["TrackingServerURL"] as! String)!)
    matomoTracker.logger = DefaultLogger(minLevel: .debug)
    return matomoTracker
}

let matomoTracker = initTracker()

struct ViewTab1: View {
    var body: some View {
        VStack {
            Text("First View")
            Text("change tab to fire page view event")
            Text("---------")
            Text("Click Button to fire play.slide.volume event with value=1.0")
            Button(action: {
                matomoTracker.track(eventWithCategory: "player", action: "slide", name: "volume", value: 1.0)
                matomoTracker.dispatch()
            }) {
                Image(systemName: "volume")
                    .font(.largeTitle)
                    .foregroundColor(.red)
            }
        }
    }
}

struct ViewTab2: View {
    var body: some View {
        VStack {
            Text("Second View")
            Text("change tab to fire page view event")
            Text("---------")
            Text("Click Button to fire play.slide.volume event with value=9.5")
            Button(action: {
                matomoTracker.track(eventWithCategory: "player", action: "slide", name: "volume", value: 9.5)
                matomoTracker.dispatch()
            }) {
                Image(systemName: "volume")
                    .font(.largeTitle)
                    .foregroundColor(.red)
            }
        }
    }
}

struct ContentView: View {
    @State private var selection = 0

    var body: some View {
        TabView(selection: $selection) {
            ViewTab1()
                .font(.title)
                .tabItem {
                    VStack {
                        Image("first")
                        Text("First")
                    }
                }
                .tag(0).onAppear{
                    print("Track First View")
                    matomoTracker.track(view: ["First View"])
                    matomoTracker.dispatch()
                }

            ViewTab2()
                .font(.title)
                .tabItem {
                    VStack {
                        Image("second")
                        Text("Second")
                    }
                }
                .tag(1).onAppear {
                    print("Track Second View")
                    matomoTracker.track(view: ["Second View"])
                    matomoTracker.dispatch()
                }
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
