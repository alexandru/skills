/**
 * Hello World Skill
 * 
 * A simple greeting function that demonstrates a basic skill structure.
 */

/**
 * Generates a greeting message
 * @param {string} name - The name to greet (defaults to "World")
 * @returns {string} A greeting message
 */
function greet(name = 'World') {
  return `Hello, ${name}!`;
}

/**
 * Generates a formal greeting message
 * @param {string} name - The name to greet
 * @returns {string} A formal greeting message
 */
function formalGreet(name) {
  return `Good day, ${name}. How are you?`;
}

module.exports = {
  greet,
  formalGreet
};

// Example usage
if (require.main === module) {
  console.log(greet());
  console.log(greet('Alice'));
  console.log(formalGreet('Bob'));
}
