package com.example.android.ui.home

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel

class HomeViewModel : ViewModel() {

    private val _text = MutableLiveData<String>().apply {
        value = "This is home Fragment\n" +
                "change tab to fire page view event\n" +
                "---------\n" +
                "Click Button to fire play.slide.volume event with value=1.0"
    }
    val text: LiveData<String> = _text
}