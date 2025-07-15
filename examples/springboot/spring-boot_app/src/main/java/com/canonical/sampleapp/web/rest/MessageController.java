package com.canonical.sampleapp.web.rest;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.canonical.sampleapp.service.MessageService;

@ConditionalOnProperty(name = "spring.rabbitmq.host")
@RestController
public class MessageController {

    private final MessageService messageService;

    public MessageController(MessageService messageService) {
        this.messageService = messageService;
    }

    // Not really very "rest"
    @GetMapping(value = "/rabbitmq/receive")
    public ResponseEntity<String> receive() {
    	String message = messageService.receive();
    	if (message == null) {
    		return ResponseEntity.notFound().build();
    	}
        return ResponseEntity.ok(message);
    }
    
    // Not really very "rest"
    @GetMapping(value = "/rabbitmq/send")
    public ResponseEntity<String> send() {
    	messageService.send("SUCCESS");
    	return ResponseEntity.ok("SUCCESS");
    }
}
