#!/usr/bin/env python3
"""
Simple script to add sample lessons to the database.
"""

import sqlite3
import hashlib

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def add_sample_lessons():
    """Add sample lessons to the database"""
    
    # Sample lessons data
    sample_lessons = [
        {
            'title': 'Introduction to Climate',
            'summary': 'A comprehensive introduction to climate science and environmental studies',
            'learning_objectives': 'Understand basic climate concepts, identify climate factors, analyze climate data',
            'focus_area': 'Science',
            'grade_level': '6-8',
            'content': '''
# Introduction to Climate

Climate refers to the long-term patterns of temperature, humidity, wind, and precipitation in a particular region. Unlike weather, which describes short-term atmospheric conditions, climate represents the average weather conditions over a period of 30 years or more.

## Key Concepts

### 1. Climate vs Weather
- **Weather**: Short-term atmospheric conditions (hours to days)
- **Climate**: Long-term average weather patterns (30+ years)

### 2. Climate Factors
- **Latitude**: Distance from equator affects temperature
- **Altitude**: Higher elevations are generally cooler
- **Ocean Currents**: Influence temperature and precipitation
- **Wind Patterns**: Affect temperature and moisture distribution
- **Landforms**: Mountains, valleys, and bodies of water

### 3. Climate Zones
- **Tropical**: Hot and humid year-round
- **Temperate**: Moderate temperatures with distinct seasons
- **Polar**: Cold temperatures year-round
- **Desert**: Hot days, cool nights, little precipitation

## Climate Change

Human activities, particularly the burning of fossil fuels, have led to increased greenhouse gas concentrations in the atmosphere, contributing to global climate change.

### Greenhouse Effect
The natural process where certain gases in Earth's atmosphere trap heat, keeping the planet warm enough to support life.

### Human Impact
- Increased CO2 emissions from burning fossil fuels
- Deforestation reducing carbon absorption
- Industrial processes releasing greenhouse gases

## Climate Data Analysis

Scientists use various tools and methods to study climate:
- Temperature records
- Ice core samples
- Tree ring analysis
- Satellite observations
- Computer models

Understanding climate is crucial for predicting weather patterns, managing natural resources, and addressing environmental challenges.
            ''',
            'is_public': 1
        },
        {
            'title': 'World History Overview',
            'summary': 'A broad survey of world history from ancient civilizations to modern times',
            'learning_objectives': 'Understand major historical periods, identify key events, analyze historical patterns',
            'focus_area': 'History',
            'grade_level': '9-12',
            'content': '''
# World History Overview

World history encompasses the study of human civilization from its earliest beginnings to the present day. This overview covers major periods and developments that have shaped our world.

## Ancient Civilizations (3500 BCE - 500 CE)

### Mesopotamia
- First known civilization
- Development of writing (cuneiform)
- Invention of the wheel
- Code of Hammurabi

### Ancient Egypt
- Nile River civilization
- Pyramids and pharaohs
- Hieroglyphic writing
- Advanced mathematics and astronomy

### Ancient Greece
- Birth of democracy
- Philosophy (Socrates, Plato, Aristotle)
- Olympic Games
- Classical art and architecture

### Ancient Rome
- Republic to Empire
- Roman law and government
- Engineering achievements (roads, aqueducts)
- Spread of Christianity

## Middle Ages (500-1500 CE)

### Early Middle Ages
- Fall of Roman Empire
- Rise of feudalism
- Spread of Christianity
- Viking invasions

### High Middle Ages
- Crusades
- Rise of towns and trade
- Gothic architecture
- Universities established

### Late Middle Ages
- Black Death
- Hundred Years' War
- Renaissance begins
- Age of Exploration starts

## Early Modern Period (1500-1800)

### Age of Exploration
- European voyages of discovery
- Columbian Exchange
- Colonial empires
- Global trade networks

### Scientific Revolution
- Copernicus and heliocentrism
- Galileo's discoveries
- Newton's laws of motion
- Scientific method

### Enlightenment
- Reason and individualism
- Political philosophy
- American and French Revolutions
- Industrial Revolution begins

## Modern Period (1800-Present)

### Industrial Revolution
- Steam power and factories
- Urbanization
- Social changes
- Economic transformation

### Age of Imperialism
- European expansion
- Scramble for Africa
- Asian colonization
- Global conflicts

### World Wars
- World War I (1914-1918)
- World War II (1939-1945)
- Cold War
- Decolonization

### Contemporary Era
- Globalization
- Technology revolution
- Environmental challenges
- Global cooperation

## Key Themes in World History

1. **Power and Politics**: How societies organize and govern themselves
2. **Economics**: How people produce, distribute, and consume goods
3. **Culture**: How people express themselves through art, religion, and ideas
4. **Technology**: How innovations change societies
5. **Environment**: How humans interact with and change their surroundings

Understanding world history helps us make sense of current events and prepare for future challenges.
            ''',
            'is_public': 1
        },
        {
            'title': 'Physics Fundamentals',
            'summary': 'Core principles of physics including mechanics, energy, and motion',
            'learning_objectives': 'Understand basic physics concepts, apply mathematical principles, solve physics problems',
            'focus_area': 'Physics',
            'grade_level': '9-12',
            'content': '''
# Physics Fundamentals

Physics is the study of matter, energy, and their interactions. It provides the foundation for understanding how the universe works, from the smallest particles to the largest galaxies.

## Mechanics

### Motion and Forces
- **Newton's Laws of Motion**:
  - First Law: Objects at rest stay at rest, objects in motion stay in motion unless acted upon by a force
  - Second Law: Force equals mass times acceleration (F = ma)
  - Third Law: For every action, there is an equal and opposite reaction

- **Types of Forces**:
  - Gravity: Attraction between masses
  - Friction: Resistance to motion
  - Normal force: Support force from surfaces
  - Applied force: Force exerted by objects

### Energy
- **Kinetic Energy**: Energy of motion (KE = ½mv²)
- **Potential Energy**: Stored energy
  - Gravitational: PE = mgh
  - Elastic: PE = ½kx²
- **Conservation of Energy**: Energy cannot be created or destroyed, only transformed

### Momentum
- **Linear Momentum**: p = mv
- **Conservation of Momentum**: Total momentum remains constant in isolated systems
- **Impulse**: Change in momentum equals force times time

## Waves and Sound

### Wave Properties
- **Amplitude**: Maximum displacement from equilibrium
- **Wavelength**: Distance between wave crests
- **Frequency**: Number of waves per second
- **Period**: Time for one complete wave cycle

### Sound Waves
- **Longitudinal waves**: Particles vibrate parallel to wave direction
- **Speed of sound**: Depends on medium (air: ~343 m/s)
- **Pitch**: Related to frequency
- **Loudness**: Related to amplitude

## Electricity and Magnetism

### Electric Charges
- **Positive and negative charges**
- **Coulomb's Law**: Force between charges
- **Electric field**: Force per unit charge

### Electric Current
- **Voltage**: Electrical pressure (V)
- **Current**: Flow of charge (I)
- **Resistance**: Opposition to current flow (R)
- **Ohm's Law**: V = IR

### Magnetism
- **Magnetic fields**: Regions of magnetic force
- **Electromagnetism**: Relationship between electricity and magnetism
- **Electromagnetic induction**: Generating current with changing magnetic fields

## Modern Physics

### Quantum Mechanics
- **Wave-particle duality**: Light and matter exhibit both wave and particle properties
- **Uncertainty principle**: Cannot simultaneously know position and momentum precisely
- **Quantum states**: Discrete energy levels

### Relativity
- **Special relativity**: Time and space are relative to observer's motion
- **E = mc²**: Mass and energy are equivalent
- **General relativity**: Gravity is curvature of spacetime

## Applications

Physics principles apply to:
- **Engineering**: Designing structures and machines
- **Medicine**: Medical imaging and radiation therapy
- **Technology**: Electronics and communications
- **Space exploration**: Rockets and satellites
- **Energy**: Power generation and conservation

Understanding physics helps us comprehend the natural world and develop technologies that improve our lives.
            ''',
            'is_public': 1
        }
    ]
    
    try:
        # Connect to database
        db = sqlite3.connect('instance/chatbot.db')
        cursor = db.cursor()
        
        # Check if we have a teacher user
        cursor.execute('SELECT id FROM users WHERE role = "teacher" LIMIT 1')
        teacher = cursor.fetchone()
        
        if not teacher:
            print("No teacher user found. Creating one...")
            # Create a teacher user
            cursor.execute('''
                INSERT INTO users (username, useremail, password, class_standard, medium, groq_api_key, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('SampleTeacher', 'teacher@example.com', hash_password('password123'), '12', 'English', '', 'teacher'))
            db.commit()
            teacher_id = cursor.lastrowid
            print(f"Created teacher user with ID: {teacher_id}")
        else:
            teacher_id = teacher[0]
            print(f"Using existing teacher user with ID: {teacher_id}")
        
        # Add sample lessons
        for lesson_data in sample_lessons:
            # Check if lesson already exists
            cursor.execute('SELECT id FROM lessons WHERE title = ?', (lesson_data['title'],))
            existing = cursor.fetchone()
            
            if existing:
                print(f"Lesson '{lesson_data['title']}' already exists (ID: {existing[0]})")
                continue
            
            # Create the lesson
            cursor.execute('''
                INSERT INTO lessons (teacher_id, title, summary, learning_objectives, focus_area, grade_level, content, is_public, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                teacher_id,
                lesson_data['title'],
                lesson_data['summary'],
                lesson_data['learning_objectives'],
                lesson_data['focus_area'],
                lesson_data['grade_level'],
                lesson_data['content'],
                lesson_data['is_public']
            ))
            db.commit()
            lesson_id = cursor.lastrowid
            print(f"Created lesson '{lesson_data['title']}' with ID: {lesson_id}")
        
        db.close()
        print("\nSample lessons added successfully!")
        print("You can now test lesson-specific questions in the chat interface.")
        
    except Exception as e:
        print(f"Error adding sample lessons: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_sample_lessons() 