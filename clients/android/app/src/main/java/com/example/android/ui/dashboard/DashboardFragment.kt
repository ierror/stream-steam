package com.example.android.ui.dashboard

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

class DashboardFragment : Fragment(), View.OnClickListener {

    private lateinit var dashboardViewModel: DashboardViewModel

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        dashboardViewModel =
            ViewModelProviders.of(this).get(DashboardViewModel::class.java)
        val root = inflater.inflate(R.layout.fragment_dashboard, container, false)
        val textView: TextView = root.findViewById(R.id.text_dashboard)
        dashboardViewModel.text.observe(viewLifecycleOwner, Observer {
            textView.text = it
        })

        val button: Button = root.findViewById(R.id.button) as Button
        button.setOnClickListener(this)

        return root
    }

    override fun onClick(view: View) {
        Log.i("track", "Track event volume=9.5")
        val tracker = (activity as MainActivity?)!!.getTracker()
        TrackHelper.track().event("player", "slide").name("volume").value(9.5f).with(tracker)
        tracker?.dispatch()
    }

    private fun trackView() {
        Log.i("track", "track view")
        val tracker = (activity as MainActivity?)!!.getTracker()
        TrackHelper.track().screen("/main_activity/dashboard").title("Dashboard").with(tracker)
        tracker?.dispatch()
        super.onResume()
    }

    override fun onResume() {
        this.trackView()
        super.onResume()
    }


}
