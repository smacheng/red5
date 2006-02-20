package org.red5.server.stream;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.red5.io.flv.FLV;
import org.red5.io.flv.FLVService;
import org.red5.io.flv.Writer;
import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.core.io.Resource;

public class StreamManager implements ApplicationContextAware {

	protected static Log log =
        LogFactory.getLog(StreamManager.class.getName());
	
	private ApplicationContext appCtx = null;
	private String streamDir = "streams";
	private HashMap published = new HashMap();
	private FLVService flvService;

	public void setApplicationContext(ApplicationContext appCtx) throws BeansException {
		this.appCtx = appCtx;
	}
	
	public void setFlvService(FLVService flvService) {
		this.flvService = flvService;
	}

	public void publishStream(Stream stream){
		
		// If we have a read mode stream, we shouldnt be publishing return
		if(stream.getMode().equals(Stream.MODE_READ)) return;
		
		MultiStreamSink multi = new MultiStreamSink();
		stream.setUpstream(multi);
		published.put(stream.getName(),multi);
		
		// If the mode is live, we dont need to do anything else
		if(stream.getMode().equals(Stream.MODE_LIVE)) return;
		
		// The mode must be record or append
		try {				
			Resource res = appCtx.getResource("streams/" + stream.getName()+".flv");
			if(stream.getMode().equals(Stream.MODE_RECORD) && res.exists()) 
				res.getFile().delete();
			if(!res.exists()) res = appCtx.getResource("streams/").createRelative(stream.getName()+".flv");
			if(!res.exists()) res.getFile().createNewFile(); 
			File file = res.getFile();
			FLV flv = flvService.getFLV(file);
			Writer writer = null; 
			if(stream.getMode().equals(Stream.MODE_RECORD)) 
				writer = flv.writer();
			else if(stream.getMode().equals(Stream.MODE_APPEND))
				writer = flv.append();
			multi.connect(new FileStreamSink(writer));
		} catch (IOException e) {
			log.error("Error recording stream: "+stream, e);
		}
	}
	
	public void deleteStream(Stream stream){
		stream.close();
		if(published.containsKey(stream.getName()))
				published.remove(stream.getName());
	}
	
	public boolean isPublishedStream(String name){
		return published.containsKey(name);
	}
	
	public void connectToPublishedStream(Stream stream){
		MultiStreamSink multi = (MultiStreamSink) published.get(stream.getName());
		multi.connect(stream);
	}
	
	public IStreamSource lookupStreamSource(String name){
		return createFileStreamSource(name);
	}

	protected IStreamSource createFileStreamSource(String name){
		Resource[] resource = null;
		FileStreamSource source = null;
		try {
			File file = appCtx.getResources("streams/" + name)[0].getFile();
			FLV flv = flvService.getFLV(file);
			source = new FileStreamSource(flv.reader());
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
		return source;
	}
	
}
