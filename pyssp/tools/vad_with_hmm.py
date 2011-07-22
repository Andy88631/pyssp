#!/usr/bin/env python
# -*- coding: utf-8 -*-
import scipy as sp
import sys
import wave
import tempfile
from pyssp.util import get_frame,add_signal,read_signal,separate_channels,uniting_channles
from pyssp.vad.ltsd import LTSD
import optparse
from scikits.learn.hmm import GaussianHMM

WINSIZE = 1024

def vad(vas,signal,winsize,window):
    out=sp.zeros(len(signal),sp.float32)
    for va in vas:
        for i in range(va[0],va[1]+2):
            add_signal(out,get_frame(signal, winsize, i)*window,winsize,i)
    return out

def write(param,signal):
    st = tempfile.TemporaryFile()
    wf=wave.open(st,'wb')
    wf.setparams(params)
    s=sp.int16(signal).tostring()
    wf.writeframes(s)
    st.seek(0)
    print st.read()

def read(fname,winsize):
    if fname =="-":
        wf=wave.open(sys.stdin,'rb')
        n=wf.getnframes()
        str=wf.readframes(n)
        params = ((wf.getnchannels(), wf.getsampwidth(),
                   wf.getframerate(), wf.getnframes(),
                   wf.getcomptype(), wf.getcompname()))
        siglen=((int )(len(str)/2/winsize) + 1) * winsize
        signal=sp.zeros(siglen, sp.int16)
        signal[0:len(str)/2] = sp.fromstring(str,sp.int16)
        return signal,params
    else:
        return read_signal(fname,winsize)


def hmm2span(ret):
    noise = ret[0]
    flag = 0
    res = []
    span=None
    for i in xrange(len(ret)):
        if ret[i]==noise:
            if flag==1:
                span.append(i-1)
                res.append(span)
                span=None
                flag=0
        else:
            if flag==0:
                span=[i]
                flag=1
    if span!=None:
        span.append(len(ret)-1)
        res.appedn(span)
    return res

if __name__ == "__main__":
    """
    python vad.py -w WINSIZE -t THREATHOLD FILENAME
    """
    parser = optparse.OptionParser(usage="%python vad [-t THREASHOLD] [-w WINSIZE] INPUTFILE \n if INPUTFILE is \"-\", read wave data from stdin")

    parser.add_option("-w", type="int", dest="winsize", default=WINSIZE)
    parser.add_option("-t", type="int", dest="th", default=30)

    (options, args) = parser.parse_args()
    windowsize = options.winsize

    fname = args[0]
    signal, params = read(fname,options.winsize)
    window = sp.hanning(windowsize)

    if params[0]==1:
        ltsd = LTSD(windowsize,window,5,lambda0=options.th)
        res,ltsds =  ltsd.compute_with_noise(signal,signal[0:windowsize*int(params[2] /float(windowsize)/3.0)])#maybe 300ms
        mhmm = GaussianHMM(n_states=2)
        x =sp.array([[i] for i in ltsds])
        mhmm.fit([x],n_iter=0)
        ret = mhmm.decode(x)[1].tolist()
        write(params,vad(hmm2span(ret),signal,windowsize,window))
    elif params[0]==2:
        l,r = separate_channels(signal)
        ltsd_l = LTSD(windowsize,window,5,lambda0=options.th)
        ltsd_r = LTSD(windowsize,window,5,lambda0=options.th)
        out = uniting_channles(vad(ltsd_l.compute_with_noise(l,l[0:windowsize*int(params[2] /float(windowsize)/3.0)])[0],l,windowsize,window),
                               vad(ltsd_r.compute_without_noise(r,r[0:windowsize*int(params[2] /float(windowsize)/3.0)])[0],r,windowsize,window))
        write(params,out)