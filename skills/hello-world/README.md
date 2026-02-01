# Hello World Skill

A simple "Hello World" skill that demonstrates the basic structure of a skill in this repository.

## Description

This skill provides a simple greeting function that returns a personalized hello message.

## Usage

```javascript
const { greet } = require('./index.js');

// Basic usage
console.log(greet());
// Output: "Hello, World!"

// With a custom name
console.log(greet('Alice'));
// Output: "Hello, Alice!"
```

## API

### `greet(name)`

Returns a greeting string.

**Parameters:**
- `name` (string, optional): The name to greet. Defaults to "World".

**Returns:**
- (string): A greeting message.

### `formalGreet(name)`

Returns a formal greeting string.

**Parameters:**
- `name` (string, optional): The name to greet. Defaults to "Sir/Madam".

**Returns:**
- (string): A formal greeting message.

## Example

```javascript
const { greet, formalGreet } = require('./index.js');

// Simple greeting
greet(); // "Hello, World!"

// Personalized greeting
greet('Bob'); // "Hello, Bob!"

// Formal greeting
formalGreet('Alice'); // "Good day, Alice. How are you?"
formalGreet(); // "Good day, Sir/Madam. How are you?"
```

## Tags

- example
- hello-world
- javascript
- beginner
