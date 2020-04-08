# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG parent_image=gcr.io/fuzzbench/base-builder
FROM $parent_image

# Need Clang/LLVM 3.8.
RUN apt-get update -y && \
    apt-get -y install llvm-3.8 \
    clang-3.8 \
    libstdc++-5-dev \
    wget \
    make \
    gcc \
    cmake \
    texinfo \
    bison \
    software-properties-common


# Set env variables.
ENV AFL_CONVERT_COMPARISON_TYPE=NONE
ENV AFL_COVERAGE_TYPE=ORIGINAL
ENV AFL_BUILD_TYPE=FUZZING
ENV AFL_DICT_TYPE=NORMAL
# TODO: update of recompile
ENV LLVM_CONFIG=llvm-config-3.8

# Download and compile aflcc.
# TODO: update of recompile
RUN git clone https://github.com/Samsung/afl_cc.git /afl && \
    cd /afl && \
    git checkout e4bed7e1113bcdfc3605b7e015a11b06604f02a3 && \
    AFL_NO_X86=1 make && \
    cd /afl/llvm_mode && \
    CC=clang-3.8 CXX=clang++-3.8 CFLAGS= CXXFLAGS= make

# Install gllvm
RUN cd /afl && \
    sh ./setup-aflc-gclang.sh

RUN apt-get install -y p7zip-full vim

# Use afl_driver.cpp from LLVM as our fuzzing library.
ENV CC=/afl/aflc-gclang
ENV CXX=/afl/aflc-gclang++
COPY aflcc_mock.c /aflcc_mock.c
# TODO: update of recompile
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/master/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    $CXX -I/usr/local/include/c++/v1/ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a afl_driver.o /afl/afl-llvm-rt.o && \
    clang-3.8 -O2 -c -fPIC /aflcc_mock.c -o /aflcc_mock.o && \
    clang-3.8 -shared -o /libAflccMock.so /aflcc_mock.o