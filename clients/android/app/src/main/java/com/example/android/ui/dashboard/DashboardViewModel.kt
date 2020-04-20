package com.example.android.ui.dashboard

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel

class DashboardViewModel : ViewModel() {

    private val _text = MutableLiveData<String>().apply {
        value = "This is dashboard Fragment\n" +
                "change tab to fire page view event\n" +
                "---------\n" +
                "Click Button to fire play.slide.volume event with value=9.5"
    }
    val text: LiveData<String> = _text
}