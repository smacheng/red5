/*
 * RED5 Open Source Flash Server - http://code.google.com/p/red5/
 * 
 * Copyright 2006-2012 by respective authors (see below). All rights reserved.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 * http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.red5.server.net.rtmp;

import java.net.InetSocketAddress;
import java.util.Map;

import org.apache.mina.core.future.ConnectFuture;
import org.apache.mina.core.future.IoFuture;
import org.apache.mina.core.future.IoFutureListener;
import org.apache.mina.transport.socket.SocketConnector;
import org.apache.mina.transport.socket.nio.NioSocketConnector;
import org.red5.server.net.rtmp.codec.RTMP;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * RTMP client object. Initial client mode code by Christian Eckerle.
 * 
 * @author The Red5 Project (red5@osflash.org)
 * @author Christian Eckerle (ce@publishing-etc.de)
 * @author Joachim Bauch (jojo@struktur.de)
 * @author Paul Gregoire (mondain@gmail.com)
 * @author Steven Gong (steven.gong@gmail.com)
 * @author Anton Lebedevich (mabrek@gmail.com)
 * @author Tiago Daniel Jacobs (tiago@imdt.com.br)
 * @author Jon Valliere
 */
public class RTMPClient extends BaseRTMPClientHandler {

	private static final Logger log = LoggerFactory.getLogger(RTMPClient.class);

	protected static final int CONNECTOR_WORKER_TIMEOUT = 7000; // seconds

	// I/O handler
	private final RTMPMinaIoHandler ioHandler;

	// Socket connector, disposed on disconnect
	protected SocketConnector socketConnector;

	// 
	protected ConnectFuture future;

	/** Constructs a new RTMPClient. */
	public RTMPClient() {
		ioHandler = new RTMPMinaIoHandler();
		ioHandler.setCodecFactory(getCodecFactory());
		ioHandler.setMode(RTMP.MODE_CLIENT);
		ioHandler.setHandler(this);
		ioHandler.setRtmpConnManager(RTMPClientConnManager.getInstance());
	}

	public Map<String, Object> makeDefaultConnectionParams(String server, int port, String application) {
		Map<String, Object> params = super.makeDefaultConnectionParams(server, port, application);
		if (!params.containsKey("tcUrl")) {
			params.put("tcUrl", String.format("rtmp://%s:%s/%s", server, port, application));
		}
		return params;
	}

	@SuppressWarnings({ "rawtypes" })
	@Override
	protected void startConnector(String server, int port) {
		socketConnector = new NioSocketConnector();
		socketConnector.setHandler(ioHandler);
		future = socketConnector.connect(new InetSocketAddress(server, port));
		future.addListener(new IoFutureListener() {
			public void operationComplete(IoFuture future) {
				try {
					// will throw RuntimeException after connection error
					future.getSession();
				} catch (Throwable e) {
					//if there isn't an ClientExceptionHandler set, a 
					//RuntimeException may be thrown in handleException
					handleException(e);
				}
			}
		});
		// Now wait for the close to be completed
		future.awaitUninterruptibly(CONNECTOR_WORKER_TIMEOUT);
	}

	@Override
	public void disconnect() {
		if (future != null) {
			// Do the close requesting that the pending messages are sent before
			// the session is closed
			try {
				future.getSession().close(false);
			} catch (Exception e) {
				log.warn("Exception during disconnect", e);
			}
			// now wait for the close to be completed
			future.awaitUninterruptibly(CONNECTOR_WORKER_TIMEOUT);
			// We can now dispose the connector
			socketConnector.dispose();
		}
		super.disconnect();
	}
}
