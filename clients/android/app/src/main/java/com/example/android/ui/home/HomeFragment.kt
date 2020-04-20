package com.example.android.ui.home

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.Observer
import androidx.lifecycle.ViewModelProviders
import com.example.android.MainActivity
import com.example.android.R
import org.matomo.sdk.extra.TrackHelper


class HomeFragment : Fragment(), View.OnClickListener {

    private lateinit var homeViewModel: HomeViewModel

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        homeViewModel =
            ViewModelProviders.of(this).get(HomeViewModel::class.java)
        val root = inflater.inflate(R.layout.fragment_home, container, false)
        val textView: TextView = root.findViewById(R.id.text_home)
        homeViewModel.text.observe(viewLifecycleOwner, Observer {
            textView.text = it
        })

        val button: Button = root.findViewById(R.id.button) as Button
        button.setOnClickListener(this)

        return root
    }

    override fun onClick(view: View) {
        Log.i("track", "Track event volume=1.0")
        val tracker = (activity as MainActivity?)!!.getTracker()
        TrackHelper.track().event("player", "slide").name("volume").value(1.0f).with(tracker)
        tracker?.dispatch()
    }

    private fun trackView() {
        Log.i("track", "track view")
        val tracker = (activity as MainActivity?)!!.getTracker()
        TrackHelper.track().screen("/main_activity/home").title("Home").with(tracker)
        tracker?.dispatch()
    }

    override fun onResume() {
        this.trackView()
        super.onResume()
    }
}
